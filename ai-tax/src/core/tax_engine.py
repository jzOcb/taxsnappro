"""
Tax Engine — Abstract interface for tax calculation.

This module defines the interface that any tax engine must implement.
Year 1: Column Tax API adapter
Year 2+: Custom engine (potentially based on IRS Direct File reference)

The engine takes a TaxReturn and produces a TaxResult with all calculated values.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from .models import TaxReturn, FilingStatus


# ============================================================
# Tax Constants (2025 Tax Year)
# ============================================================

TAX_YEAR = 2025

# Federal tax brackets 2025 (MFJ)
FEDERAL_BRACKETS_MFJ = [
    (Decimal("23850"), Decimal("0.10")),
    (Decimal("96950"), Decimal("0.12")),
    (Decimal("206700"), Decimal("0.22")),
    (Decimal("394600"), Decimal("0.24")),
    (Decimal("501050"), Decimal("0.32")),
    (Decimal("751600"), Decimal("0.35")),
    (Decimal("999999999"), Decimal("0.37")),
]

FEDERAL_BRACKETS_SINGLE = [
    (Decimal("11925"), Decimal("0.10")),
    (Decimal("48475"), Decimal("0.12")),
    (Decimal("103350"), Decimal("0.22")),
    (Decimal("197300"), Decimal("0.24")),
    (Decimal("250525"), Decimal("0.32")),
    (Decimal("626350"), Decimal("0.35")),
    (Decimal("999999999"), Decimal("0.37")),
]

# Standard deduction 2025
STANDARD_DEDUCTION = {
    FilingStatus.SINGLE: Decimal("15000"),
    FilingStatus.MARRIED_FILING_JOINTLY: Decimal("30000"),
    FilingStatus.MARRIED_FILING_SEPARATELY: Decimal("15000"),
    FilingStatus.HEAD_OF_HOUSEHOLD: Decimal("22500"),
    FilingStatus.QUALIFYING_SURVIVING_SPOUSE: Decimal("30000"),
}

# LTCG brackets 2025 (MFJ)
LTCG_BRACKETS_MFJ = [
    (Decimal("96700"), Decimal("0.00")),
    (Decimal("600050"), Decimal("0.15")),
    (Decimal("999999999"), Decimal("0.20")),
]

# Additional Medicare Tax
ADDITIONAL_MEDICARE_THRESHOLD_MFJ = Decimal("250000")
ADDITIONAL_MEDICARE_RATE = Decimal("0.009")

# Net Investment Income Tax (NIIT)
NIIT_THRESHOLD_MFJ = Decimal("250000")
NIIT_RATE = Decimal("0.038")

# SALT cap
SALT_CAP = Decimal("10000")

# HSA limits 2025
HSA_LIMIT_SELF = Decimal("4300")
HSA_LIMIT_FAMILY = Decimal("8550")
HSA_CATCHUP_55 = Decimal("1000")

# 401(k) limits 2025
K401_EMPLOYEE_LIMIT = Decimal("23500")
K401_CATCHUP_50 = Decimal("7500")
K401_CATCHUP_60_63 = Decimal("11250")
K401_TOTAL_LIMIT = Decimal("70000")

# Massachusetts
MA_TAX_RATE = Decimal("0.05")
MA_STCG_RATE = Decimal("0.085")
MA_LTCG_RATE = Decimal("0.05")
MA_MILLIONAIRE_SURTAX_THRESHOLD = Decimal("1000000")
MA_MILLIONAIRE_SURTAX_RATE = Decimal("0.04")


# ============================================================
# Tax Result
# ============================================================

@dataclass
class TaxLineItem:
    """A single line item in the tax calculation."""
    form: str = ""       # e.g., "1040", "Schedule A"
    line: str = ""       # e.g., "1", "7a"
    description: str = ""
    amount: Decimal = Decimal("0")


@dataclass
class TaxResult:
    """Complete result of a tax calculation."""
    tax_year: int = TAX_YEAR
    
    # Gross income
    total_income: Decimal = Decimal("0")
    
    # Adjustments (above-the-line)
    total_adjustments: Decimal = Decimal("0")
    adjusted_gross_income: Decimal = Decimal("0")
    
    # Deductions
    standard_deduction: Decimal = Decimal("0")
    itemized_deduction: Decimal = Decimal("0")
    deduction_used: Decimal = Decimal("0")  # max(standard, itemized)
    qualified_business_income_deduction: Decimal = Decimal("0")
    
    # Taxable income
    taxable_income: Decimal = Decimal("0")
    
    # Federal tax
    regular_tax: Decimal = Decimal("0")
    amt: Decimal = Decimal("0")  # Alternative Minimum Tax
    additional_medicare_tax: Decimal = Decimal("0")
    niit: Decimal = Decimal("0")  # Net Investment Income Tax
    total_federal_tax: Decimal = Decimal("0")
    
    # Credits
    child_tax_credit: Decimal = Decimal("0")
    other_credits: Decimal = Decimal("0")
    total_credits: Decimal = Decimal("0")
    
    # Payments
    total_withholding: Decimal = Decimal("0")
    estimated_payments: Decimal = Decimal("0")
    total_payments: Decimal = Decimal("0")
    
    # Result
    federal_tax_owed: Decimal = Decimal("0")  # Positive = owe, Negative = refund
    federal_refund: Decimal = Decimal("0")
    
    # State (MA)
    state_taxable_income: Decimal = Decimal("0")
    state_tax: Decimal = Decimal("0")
    state_withholding: Decimal = Decimal("0")
    state_tax_owed: Decimal = Decimal("0")
    state_refund: Decimal = Decimal("0")
    
    # Effective rates
    effective_federal_rate: Decimal = Decimal("0")
    effective_total_rate: Decimal = Decimal("0")
    marginal_federal_rate: Decimal = Decimal("0")
    
    # Detailed line items
    line_items: list[TaxLineItem] = field(default_factory=list)
    
    # Optimization suggestions
    optimization_notes: list[str] = field(default_factory=list)
    potential_savings: Decimal = Decimal("0")
    
    # Validation
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    is_valid: bool = True


# ============================================================
# Tax Engine Interface
# ============================================================

class TaxEngine(ABC):
    """
    Abstract tax calculation engine.
    
    Implementations:
    - ColumnTaxEngine: Uses Column Tax API for calculations
    - CustomTaxEngine: Our own calculation engine (Year 2+)
    """
    
    @abstractmethod
    def calculate(self, tax_return: TaxReturn) -> TaxResult:
        """
        Calculate taxes for the given tax return.
        
        Args:
            tax_return: Complete tax return data
            
        Returns:
            TaxResult with all calculated values
        """
        pass
    
    @abstractmethod
    def validate(self, tax_return: TaxReturn) -> list[str]:
        """
        Validate tax return data for completeness and consistency.
        
        Returns:
            List of validation error messages (empty = valid)
        """
        pass
    
    @abstractmethod
    def generate_xml(self, tax_return: TaxReturn, result: TaxResult) -> str:
        """
        Generate IRS MeF-compliant XML for e-filing.
        
        Returns:
            XML string conforming to IRS schemas
        """
        pass


# ============================================================
# Simple Calculator (for estimation / testing)
# ============================================================

class SimpleEstimator:
    """
    Quick tax estimator using basic bracket math.
    NOT for filing — only for giving users a rough estimate during the interview.
    """
    
    @staticmethod
    def estimate_federal_tax(taxable_income: Decimal, 
                              filing_status: FilingStatus = FilingStatus.MARRIED_FILING_JOINTLY) -> Decimal:
        """Estimate federal income tax using brackets."""
        if filing_status == FilingStatus.MARRIED_FILING_JOINTLY:
            brackets = FEDERAL_BRACKETS_MFJ
        else:
            brackets = FEDERAL_BRACKETS_SINGLE
        
        tax = Decimal("0")
        prev_limit = Decimal("0")
        
        for limit, rate in brackets:
            if taxable_income <= prev_limit:
                break
            taxable_at_rate = min(taxable_income, limit) - prev_limit
            tax += taxable_at_rate * rate
            prev_limit = limit
        
        return tax.quantize(Decimal("0.01"))
    
    @staticmethod
    def estimate_ma_tax(taxable_income: Decimal,
                         short_term_gains: Decimal = Decimal("0")) -> Decimal:
        """Estimate Massachusetts state tax."""
        # Regular income at 5%
        regular_tax = (taxable_income - short_term_gains) * MA_TAX_RATE
        # Short-term gains at 8.5%
        stcg_tax = short_term_gains * MA_STCG_RATE
        # Millionaire's surtax
        surtax = Decimal("0")
        if taxable_income > MA_MILLIONAIRE_SURTAX_THRESHOLD:
            surtax = (taxable_income - MA_MILLIONAIRE_SURTAX_THRESHOLD) * MA_MILLIONAIRE_SURTAX_RATE
        
        return (regular_tax + stcg_tax + surtax).quantize(Decimal("0.01"))
    
    def quick_estimate(self, tax_return: TaxReturn) -> dict:
        """
        Quick estimate for display during the interview.
        Returns a dict with key figures.
        """
        gross = tax_return.gross_income
        deduction = STANDARD_DEDUCTION.get(tax_return.filing_status, Decimal("30000"))
        
        # HSA deduction
        hsa_deduction = Decimal("0")
        if tax_return.hsa:
            hsa_deduction = tax_return.hsa.contributions_personal
        
        # 401k is already excluded from W-2 Box 1, so no adjustment needed
        
        agi = gross - hsa_deduction
        taxable = max(agi - deduction, Decimal("0"))
        
        federal_tax = self.estimate_federal_tax(taxable, tax_return.filing_status)
        
        # Additional Medicare
        medicare_extra = Decimal("0")
        if tax_return.total_w2_wages > ADDITIONAL_MEDICARE_THRESHOLD_MFJ:
            medicare_extra = (tax_return.total_w2_wages - ADDITIONAL_MEDICARE_THRESHOLD_MFJ) * ADDITIONAL_MEDICARE_RATE
        
        # NIIT
        niit = Decimal("0")
        investment_income = (tax_return.total_interest_income + 
                           tax_return.total_dividend_income +
                           (tax_return.capital_gains.net_gain if tax_return.capital_gains else Decimal("0")))
        if agi > NIIT_THRESHOLD_MFJ:
            niit = min(investment_income, agi - NIIT_THRESHOLD_MFJ) * NIIT_RATE
        
        total_federal = federal_tax + medicare_extra + niit
        total_withholding = tax_return.total_federal_withholding + tax_return.estimated_tax_payments
        
        # MA
        ma_tax = self.estimate_ma_tax(agi)  # Simplified — uses AGI not MA-specific
        
        return {
            "gross_income": gross,
            "agi": agi,
            "taxable_income": taxable,
            "federal_tax": total_federal,
            "federal_withholding": total_withholding,
            "federal_owed_or_refund": total_federal - total_withholding,
            "ma_tax": ma_tax,
            "effective_rate": (total_federal / gross * 100).quantize(Decimal("0.1")) if gross > 0 else Decimal("0"),
            "marginal_rate": Decimal("35"),  # Simplified for $500K+
        }
