"""
Return Processor — Process a complete tax return through the Fact Graph.

This is the main orchestrator that:
1. Takes raw tax data (from documents or manual entry)
2. Populates the Fact Graph
3. Runs all calculations
4. Generates a summary with line-by-line breakdown
5. Identifies optimization opportunities

Usage:
    processor = ReturnProcessor(tax_year=2024)
    processor.set_filing_status("married_filing_jointly")
    processor.add_w2(wages=275000, fed_withheld=50000, ...)
    processor.add_1099_int(interest=5000, ...)
    ...
    result = processor.calculate()
    print(result.summary())
"""

from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from typing import Optional, Any
import json

from .fact_graph import FactGraph, FactType
from .modules.federal_core import (
    register_all_federal_core,
    _compute_bracket_tax,
    _get_rounded_taxable_income,
)
from .modules.income_sources import build_income_sources
from .modules.investments import build_all_investment_modules
from .tax_constants import get_constants, TaxYearConstants
from .security import mask_ssn, mask_ein, sanitize_dict_for_log, SecureLogger

logger = SecureLogger(__name__)


def _d(val) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


@dataclass
class TaxSummaryLine:
    """A single line in the tax summary."""
    line_number: str
    description: str
    amount: Decimal = Decimal("0")
    notes: str = ""


@dataclass
class TaxResult:
    """Complete tax calculation result."""
    tax_year: int = 2024
    filing_status: str = ""
    
    # Income
    total_wages: Decimal = Decimal("0")
    total_interest: Decimal = Decimal("0")
    total_dividends: Decimal = Decimal("0")
    qualified_dividends: Decimal = Decimal("0")
    capital_gains: Decimal = Decimal("0")
    rental_income: Decimal = Decimal("0")
    other_income: Decimal = Decimal("0")
    total_income: Decimal = Decimal("0")
    
    # Adjustments
    hsa_deduction: Decimal = Decimal("0")
    student_loan_interest: Decimal = Decimal("0")
    other_adjustments: Decimal = Decimal("0")
    total_adjustments: Decimal = Decimal("0")
    agi: Decimal = Decimal("0")
    
    # Deductions
    standard_deduction: Decimal = Decimal("0")
    itemized_deduction: Decimal = Decimal("0")
    deduction_used: Decimal = Decimal("0")
    deduction_type: str = "standard"
    taxable_income: Decimal = Decimal("0")
    
    # Tax
    tax_from_brackets: Decimal = Decimal("0")
    additional_medicare_tax: Decimal = Decimal("0")
    niit: Decimal = Decimal("0")
    total_tax: Decimal = Decimal("0")
    
    # Payments
    federal_withholding: Decimal = Decimal("0")
    estimated_payments: Decimal = Decimal("0")
    total_payments: Decimal = Decimal("0")
    
    # Result
    refund: Decimal = Decimal("0")
    balance_due: Decimal = Decimal("0")
    
    # State
    state: str = ""
    state_taxable_income: Decimal = Decimal("0")
    state_tax: Decimal = Decimal("0")
    state_withholding: Decimal = Decimal("0")
    state_refund: Decimal = Decimal("0")
    state_balance_due: Decimal = Decimal("0")
    
    # Effective rates
    effective_federal_rate: Decimal = Decimal("0")
    effective_total_rate: Decimal = Decimal("0")
    marginal_rate: Decimal = Decimal("0")
    
    # Optimization opportunities
    optimizations: list[str] = field(default_factory=list)
    
    # Line-by-line for Form 1040
    lines_1040: list[TaxSummaryLine] = field(default_factory=list)
    
    def summary(self) -> str:
        """Generate human-readable tax summary."""
        lines = []
        lines.append(f"{'='*60}")
        lines.append(f"  TAX RETURN SUMMARY — {self.tax_year}")
        lines.append(f"  Filing Status: {self.filing_status}")
        lines.append(f"{'='*60}")
        lines.append("")
        
        lines.append("📊 INCOME")
        lines.append(f"  Wages (W-2):              ${self.total_wages:>12,.2f}")
        if self.total_interest > 0:
            lines.append(f"  Interest Income:          ${self.total_interest:>12,.2f}")
        if self.total_dividends > 0:
            lines.append(f"  Dividends:                ${self.total_dividends:>12,.2f}")
        if self.qualified_dividends > 0:
            lines.append(f"    (Qualified):            ${self.qualified_dividends:>12,.2f}")
        if self.capital_gains != 0:
            lines.append(f"  Capital Gains/Losses:     ${self.capital_gains:>12,.2f}")
        if self.rental_income != 0:
            lines.append(f"  Rental Income:            ${self.rental_income:>12,.2f}")
        if self.other_income != 0:
            lines.append(f"  Other Income:             ${self.other_income:>12,.2f}")
        lines.append(f"  ─────────────────────────────────────")
        lines.append(f"  Total Income (Line 9):    ${self.total_income:>12,.2f}")
        lines.append("")
        
        if self.total_adjustments > 0:
            lines.append("📉 ADJUSTMENTS")
            if self.hsa_deduction > 0:
                lines.append(f"  HSA Deduction:            ${self.hsa_deduction:>12,.2f}")
            if self.student_loan_interest > 0:
                lines.append(f"  Student Loan Interest:    ${self.student_loan_interest:>12,.2f}")
            lines.append(f"  Total Adjustments:        ${self.total_adjustments:>12,.2f}")
            lines.append("")
        
        lines.append(f"  AGI (Line 11):            ${self.agi:>12,.2f}")
        lines.append("")
        
        lines.append("📋 DEDUCTIONS")
        lines.append(f"  Standard Deduction:       ${self.standard_deduction:>12,.2f}")
        if self.itemized_deduction > 0:
            lines.append(f"  Itemized Deduction:       ${self.itemized_deduction:>12,.2f}")
        lines.append(f"  → Using: {self.deduction_type.upper()}")
        lines.append(f"  Deduction Applied:        ${self.deduction_used:>12,.2f}")
        lines.append(f"  Taxable Income (Line 15): ${self.taxable_income:>12,.2f}")
        lines.append("")
        
        lines.append("💰 TAX")
        lines.append(f"  Tax from Brackets:        ${self.tax_from_brackets:>12,.2f}")
        if self.additional_medicare_tax > 0:
            lines.append(f"  Additional Medicare Tax:  ${self.additional_medicare_tax:>12,.2f}")
        if self.niit > 0:
            lines.append(f"  Net Investment Income Tax:${self.niit:>12,.2f}")
        lines.append(f"  ─────────────────────────────────────")
        lines.append(f"  Total Tax (Line 24):      ${self.total_tax:>12,.2f}")
        lines.append("")
        
        lines.append("💳 PAYMENTS")
        lines.append(f"  Federal Withholding:      ${self.federal_withholding:>12,.2f}")
        if self.estimated_payments > 0:
            lines.append(f"  Estimated Payments:       ${self.estimated_payments:>12,.2f}")
        lines.append(f"  Total Payments (Line 33): ${self.total_payments:>12,.2f}")
        lines.append("")
        
        if self.refund > 0:
            lines.append(f"  ✅ REFUND:                ${self.refund:>12,.2f}")
        elif self.balance_due > 0:
            lines.append(f"  ⚠️  BALANCE DUE:          ${self.balance_due:>12,.2f}")
        else:
            lines.append(f"  ✅ EVEN — no refund, no balance due")
        lines.append("")
        
        if self.state:
            lines.append(f"🏛️  STATE ({self.state})")
            lines.append(f"  State Taxable Income:     ${self.state_taxable_income:>12,.2f}")
            lines.append(f"  State Tax:                ${self.state_tax:>12,.2f}")
            lines.append(f"  State Withholding:        ${self.state_withholding:>12,.2f}")
            if self.state_refund > 0:
                lines.append(f"  State Refund:             ${self.state_refund:>12,.2f}")
            elif self.state_balance_due > 0:
                lines.append(f"  State Balance Due:        ${self.state_balance_due:>12,.2f}")
            lines.append("")
        
        lines.append("📈 EFFECTIVE RATES")
        lines.append(f"  Federal Effective Rate:   {self.effective_federal_rate:.1%}")
        lines.append(f"  Total Effective Rate:     {self.effective_total_rate:.1%}")
        lines.append(f"  Marginal Federal Rate:    {self.marginal_rate:.0%}")
        lines.append("")
        
        if self.optimizations:
            lines.append("💡 OPTIMIZATION OPPORTUNITIES")
            for opt in self.optimizations:
                lines.append(f"  • {opt}")
            lines.append("")
        
        lines.append(f"{'='*60}")
        return "\n".join(lines)


class ReturnProcessor:
    """
    Main tax return processor.
    
    Builds a Fact Graph, populates it with user data, 
    runs calculations, and produces results.
    """
    
    def __init__(self, tax_year: int = 2024):
        self.tax_year = tax_year
        self.graph = FactGraph()
        self._filing_status = None
        self._w2_data = []
        self._spouse_w2_data = []
        self._interest_data = []
        self._dividend_data = []
        self._state = "MA"
        self._itemized = {}
        self._capital_gains = Decimal("0")
        self._rental_income = Decimal("0")
        self._hsa_deduction = Decimal("0")
        self._estimated_payments = Decimal("0")
        self._other_income = Decimal("0")
        self._state_withholding = Decimal("0")
        self._initialized = False
    
    def set_filing_status(self, status: str):
        """Set filing status: single, married_filing_jointly, etc."""
        self._filing_status = status
    
    def set_state(self, state: str):
        """Set state for state tax calculation."""
        self._state = state
    
    def add_w2(self, employer_name: str = "", wages: Decimal = Decimal("0"),
               federal_withheld: Decimal = Decimal("0"),
               ss_wages: Decimal = Decimal("0"), ss_tax: Decimal = Decimal("0"),
               medicare_wages: Decimal = Decimal("0"), medicare_tax: Decimal = Decimal("0"),
               state_wages: Decimal = Decimal("0"), state_withheld: Decimal = Decimal("0"),
               retirement_plan: bool = False,
               box12_w_hsa: Decimal = Decimal("0"),
               box12_dd_health: Decimal = Decimal("0"),
               box12_d_401k: Decimal = Decimal("0"),
               filer: str = "primary", **kwargs):
        """Add a W-2 form."""
        data = {
            'employer_name': employer_name,
            'wages': _d(wages),
            'federal_withheld': _d(federal_withheld),
            'ss_wages': _d(ss_wages),
            'ss_tax': _d(ss_tax),
            'medicare_wages': _d(medicare_wages),
            'medicare_tax': _d(medicare_tax),
            'state_wages': _d(state_wages),
            'state_withheld': _d(state_withheld),
            'retirement_plan': retirement_plan,
            'box12_w_hsa': _d(box12_w_hsa),
            'box12_dd_health': _d(box12_dd_health),
            'box12_d_401k': _d(box12_d_401k),
            'filer': filer,
        }
        data.update(kwargs)
        
        if filer == "spouse":
            self._spouse_w2_data.append(data)
        else:
            self._w2_data.append(data)
        
        logger.info(f"Added W-2: {employer_name}, wages=${wages:,.2f}")
    
    def add_1099_int(self, payer: str = "", interest: Decimal = Decimal("0"),
                     tax_exempt: Decimal = Decimal("0"),
                     federal_withheld: Decimal = Decimal("0"), **kwargs):
        """Add a 1099-INT."""
        self._interest_data.append({
            'payer': payer,
            'interest': _d(interest),
            'tax_exempt': _d(tax_exempt),
            'federal_withheld': _d(federal_withheld),
            **kwargs,
        })
    
    def add_1099_div(self, payer: str = "", ordinary: Decimal = Decimal("0"),
                     qualified: Decimal = Decimal("0"),
                     capital_gain: Decimal = Decimal("0"),
                     federal_withheld: Decimal = Decimal("0"),
                     foreign_tax: Decimal = Decimal("0"), **kwargs):
        """Add a 1099-DIV."""
        self._dividend_data.append({
            'payer': payer,
            'ordinary': _d(ordinary),
            'qualified': _d(qualified),
            'capital_gain': _d(capital_gain),
            'federal_withheld': _d(federal_withheld),
            'foreign_tax': _d(foreign_tax),
            **kwargs,
        })
    
    def set_capital_gains(self, net_amount: Decimal):
        """Set net capital gains/losses from Schedule D."""
        self._capital_gains = _d(net_amount)
    
    def set_rental_income(self, net_amount: Decimal):
        """Set net rental income/loss from Schedule E."""
        self._rental_income = _d(net_amount)
    
    def set_hsa_deduction(self, amount: Decimal):
        """Set HSA deduction amount."""
        self._hsa_deduction = _d(amount)
    
    def set_estimated_payments(self, amount: Decimal):
        """Set estimated tax payments."""
        self._estimated_payments = _d(amount)
    
    def set_other_income(self, amount: Decimal):
        """Set other income (Schedule 1 line 8)."""
        self._other_income = _d(amount)
    
    def set_itemized_deductions(self, state_tax: Decimal = Decimal("0"),
                                 property_tax: Decimal = Decimal("0"),
                                 mortgage_interest: Decimal = Decimal("0"),
                                 charity: Decimal = Decimal("0"),
                                 medical: Decimal = Decimal("0"),
                                 **kwargs):
        """Set itemized deduction amounts for Schedule A."""
        self._itemized = {
            'state_tax': _d(state_tax),
            'property_tax': _d(property_tax),
            'mortgage_interest': _d(mortgage_interest),
            'charity': _d(charity),
            'medical': _d(medical),
        }
        self._itemized.update(kwargs)
    
    def _init_graph(self):
        """Initialize the Fact Graph with all modules."""
        if self._initialized:
            return
        
        # Register all federal core modules
        register_all_federal_core(self.graph)
        
        self._initialized = True
    
    def calculate(self) -> TaxResult:
        """
        Run the full tax calculation and return results.
        Uses tax year-specific constants (2024 vs 2025 brackets, deductions, etc.)
        """
        self._init_graph()
        self._tc = get_constants(self.tax_year)
        result = TaxResult(tax_year=self.tax_year)
        
        # --- Filing status ---
        status = self._filing_status or "married_filing_jointly"
        result.filing_status = status
        self.graph.set("/filingStatus", status)
        
        # --- Aggregate W-2 data ---
        total_wages = sum(w['wages'] for w in self._w2_data)
        total_fed_wh = sum(w['federal_withheld'] for w in self._w2_data)
        total_medicare_wages = sum(w['medicare_wages'] for w in self._w2_data)
        total_medicare_tax = sum(w['medicare_tax'] for w in self._w2_data)
        total_state_wh = sum(w['state_withheld'] for w in self._w2_data)
        
        # Add spouse W-2s
        total_wages += sum(w['wages'] for w in self._spouse_w2_data)
        total_fed_wh += sum(w['federal_withheld'] for w in self._spouse_w2_data)
        total_medicare_wages += sum(w['medicare_wages'] for w in self._spouse_w2_data)
        total_medicare_tax += sum(w['medicare_tax'] for w in self._spouse_w2_data)
        total_state_wh += sum(w['state_withheld'] for w in self._spouse_w2_data)
        
        result.total_wages = total_wages
        result.federal_withholding = total_fed_wh
        self._state_withholding = total_state_wh
        
        # Set writable facts
        self.graph.set("/totalW2Wages", total_wages)
        self.graph.set("/totalW2MedicareWages", total_medicare_wages)
        self.graph.set("/totalW2MedicareTax", total_medicare_tax)
        self.graph.set("/formW2Withholding", total_fed_wh)
        
        # --- Interest income ---
        total_interest = sum(i['interest'] for i in self._interest_data)
        total_tax_exempt_interest = sum(i.get('tax_exempt', Decimal("0")) for i in self._interest_data)
        result.total_interest = total_interest
        
        if total_interest > 0:
            # Set the writable fact for interest
            int_fact = self.graph.get_fact("/interestReports/0/1099Amount")
            if int_fact:
                self.graph.set("/interestReports/0/has1099", True)
                self.graph.set("/interestReports/0/1099Amount", total_interest)
            else:
                # Fall back to direct path if interest module not loaded
                int_fact2 = self.graph.get_fact("/totalInterestIncome")
                if int_fact2 and int_fact2.is_writable:
                    self.graph.set("/totalInterestIncome", total_interest)
        
        # --- Dividend income ---
        total_ordinary_div = sum(d['ordinary'] for d in self._dividend_data)
        total_qualified_div = sum(d['qualified'] for d in self._dividend_data)
        result.total_dividends = total_ordinary_div
        result.qualified_dividends = total_qualified_div
        
        ord_div_fact = self.graph.get_fact("/ordinaryDividends")
        if ord_div_fact and ord_div_fact.is_writable:
            self.graph.set("/ordinaryDividends", total_ordinary_div)
        qual_div_fact = self.graph.get_fact("/qualifiedDividends")
        if qual_div_fact and qual_div_fact.is_writable:
            self.graph.set("/qualifiedDividends", total_qualified_div)
        
        # --- Capital gains ---
        result.capital_gains = self._capital_gains
        cap_fact = self.graph.get_fact("/capitalGainsOrLosses")
        if cap_fact and cap_fact.is_writable:
            self.graph.set("/capitalGainsOrLosses", self._capital_gains)
        
        # --- Rental income ---
        result.rental_income = self._rental_income
        # Rental flows through otherIncome for now
        total_other = self._other_income + self._rental_income
        result.other_income = total_other
        other_fact = self.graph.get_fact("/otherIncome")
        if other_fact and other_fact.is_writable:
            self.graph.set("/otherIncome", total_other)
        
        # --- HSA deduction ---
        result.hsa_deduction = self._hsa_deduction
        hsa_fact = self.graph.get_fact("/hsaDeduction")
        if hsa_fact and hsa_fact.is_writable:
            self.graph.set("/hsaDeduction", self._hsa_deduction)
        
        # --- Estimated payments ---
        result.estimated_payments = self._estimated_payments
        est_fact = self.graph.get_fact("/estimatedTaxPayments")
        if est_fact and est_fact.is_writable:
            self.graph.set("/estimatedTaxPayments", self._estimated_payments)
        
        # --- Force evaluation ---
        self.graph._dirty = True
        self.graph._evaluate_all()
        
        # --- Read computed values ---
        result.total_income = _d(self.graph.get("/totalIncome"))
        result.total_adjustments = _d(self.graph.get("/adjustmentsToIncome"))
        result.agi = _d(self.graph.get("/agi"))
        
        # Use year-specific standard deduction (override graph's hardcoded 2025 values)
        tc = self._tc
        if status in ("married_filing_jointly", "qualifying_surviving_spouse"):
            result.standard_deduction = tc.std_deduction_mfj
        elif status == "head_of_household":
            result.standard_deduction = tc.std_deduction_hoh
        elif status == "married_filing_separately":
            result.standard_deduction = tc.std_deduction_mfs
        else:
            result.standard_deduction = tc.std_deduction_single
        
        result.taxable_income = max(result.agi - result.standard_deduction, Decimal("0"))
        
        # --- Itemized deduction check ---
        if self._itemized:
            itemized_total = self._calc_itemized_deduction(result.agi)
            result.itemized_deduction = itemized_total
            if itemized_total > result.standard_deduction:
                result.deduction_type = "itemized"
                result.deduction_used = itemized_total
                result.taxable_income = max(result.agi - itemized_total, Decimal("0"))
            else:
                result.deduction_type = "standard"
                result.deduction_used = result.standard_deduction
        else:
            result.deduction_type = "standard"
            result.deduction_used = result.standard_deduction
        
        # --- Tax from brackets (always use year-specific brackets) ---
        brackets = self._get_brackets(status)
        rounded_ti = _get_rounded_taxable_income(result.taxable_income)
        result.tax_from_brackets = _compute_bracket_tax(rounded_ti, brackets)
        
        # --- Additional taxes ---
        result.additional_medicare_tax = _d(self.graph.get("/additionalMedicareTax"))
        result.niit = _d(self.graph.get("/netInvestmentIncomeTax"))
        
        # Recalculate NIIT with year-specific thresholds
        if status == "married_filing_jointly":
            niit_threshold = tc.niit_threshold_mfj
        elif status == "married_filing_separately":
            niit_threshold = tc.niit_threshold_mfs
        else:
            niit_threshold = tc.niit_threshold_other
        
        net_invest = max(
            result.total_interest + result.total_dividends + 
            max(result.capital_gains, Decimal("0")) + 
            max(result.rental_income, Decimal("0")),
            Decimal("0")
        )
        magi_excess = max(result.agi - niit_threshold, Decimal("0"))
        result.niit = (Decimal("0.038") * min(net_invest, magi_excess)).quantize(Decimal("1"))
        
        # --- Total tax ---
        result.total_tax = result.tax_from_brackets + result.additional_medicare_tax + result.niit
        
        # --- Payments ---
        result.total_payments = result.federal_withholding + result.estimated_payments
        
        # --- Refund or balance due ---
        if result.total_payments > result.total_tax:
            result.refund = result.total_payments - result.total_tax
        else:
            result.balance_due = result.total_tax - result.total_payments
        
        # --- State tax (MA) ---
        if self._state == "MA":
            self._calc_ma_tax(result)
        
        # --- Effective rates ---
        if result.agi > 0:
            result.effective_federal_rate = result.total_tax / result.agi
            total_tax_all = result.total_tax + result.state_tax
            result.effective_total_rate = total_tax_all / result.agi
        
        result.marginal_rate = self._get_marginal_rate(result.taxable_income, status)
        
        # --- Optimization opportunities ---
        self._find_optimizations(result)
        
        return result
    
    def _calc_itemized_deduction(self, agi: Decimal) -> Decimal:
        """Calculate itemized deduction (Schedule A) with year-specific SALT cap."""
        tc = self._tc
        salt = min(
            self._itemized.get('state_tax', Decimal("0")) + 
            self._itemized.get('property_tax', Decimal("0")),
            tc.salt_cap  # $10K for 2024, $40K for 2025 (OBBBA)
        )
        
        mortgage = self._itemized.get('mortgage_interest', Decimal("0"))
        charity = self._itemized.get('charity', Decimal("0"))
        
        # Medical: only amount exceeding 7.5% of AGI
        medical = self._itemized.get('medical', Decimal("0"))
        medical_deductible = max(medical - agi * Decimal("0.075"), Decimal("0"))
        
        return salt + mortgage + charity + medical_deductible
    
    def _get_brackets(self, status: str) -> list:
        """Get year-specific bracket table for filing status."""
        tc = self._tc
        if status in ("married_filing_jointly", "qualifying_surviving_spouse"):
            return list(tc.brackets_mfj)
        elif status == "head_of_household":
            return list(tc.brackets_hoh)
        elif status == "married_filing_separately":
            return list(tc.brackets_mfs)
        return list(tc.brackets_single)
    
    def _get_marginal_rate(self, taxable_income: Decimal, status: str) -> Decimal:
        """Get marginal tax rate."""
        brackets = self._get_brackets(status)
        for upper, rate, _, _ in brackets:
            if upper is None or taxable_income <= upper:
                return rate
        return Decimal("0.37")
    
    def _calc_ma_tax(self, result: TaxResult):
        """Calculate Massachusetts state income tax with year-specific constants."""
        result.state = "MA"
        tc = self._tc
        
        # MA taxable income ≈ federal AGI - MA personal exemption
        if self._filing_status in ("married_filing_jointly", "qualifying_surviving_spouse"):
            ma_exemption = tc.ma_exemption_mfj
        elif self._filing_status == "head_of_household":
            ma_exemption = tc.ma_exemption_hoh
        else:
            ma_exemption = tc.ma_exemption_single
        
        ma_taxable = max(result.agi - ma_exemption, Decimal("0"))
        result.state_taxable_income = ma_taxable
        
        # Base tax at 5%
        state_tax = (ma_taxable * tc.ma_rate).quantize(Decimal("1"))
        
        # MA millionaire surtax: 4% on income over threshold
        if result.agi > tc.ma_surtax_threshold:
            surtax = ((result.agi - tc.ma_surtax_threshold) * tc.ma_surtax_rate).quantize(Decimal("1"))
            state_tax += surtax
        
        result.state_tax = state_tax
        result.state_withholding = self._state_withholding
        
        if result.state_withholding > result.state_tax:
            result.state_refund = result.state_withholding - result.state_tax
        else:
            result.state_balance_due = result.state_tax - result.state_withholding
    
    def _find_optimizations(self, result: TaxResult):
        """Identify tax optimization opportunities."""
        opts = []
        
        # Check if itemizing would help
        if result.deduction_type == "standard" and result.itemized_deduction > 0:
            diff = result.standard_deduction - result.itemized_deduction
            if diff < Decimal("3000"):
                opts.append(
                    f"Itemized deduction (${result.itemized_deduction:,.0f}) is close to standard "
                    f"(${result.standard_deduction:,.0f}). Consider bunching deductions."
                )
        
        # HSA max-out check (year-specific limits)
        tc = self._tc if hasattr(self, '_tc') else get_constants(self.tax_year)
        if result.filing_status == "married_filing_jointly":
            hsa_limit = tc.hsa_family
        else:
            hsa_limit = tc.hsa_self
        
        if result.hsa_deduction < hsa_limit and result.hsa_deduction > 0:
            opts.append(
                f"HSA contribution (${result.hsa_deduction:,.0f}) is below the "
                f"${hsa_limit:,.0f} limit. Max it out for additional tax savings."
            )
        
        # High income + NIIT
        if result.niit > 0:
            opts.append(
                f"Paying ${result.niit:,.0f} in NIIT (3.8%). Consider tax-loss harvesting "
                "or municipal bonds to reduce investment income."
            )
        
        # Additional Medicare Tax
        if result.additional_medicare_tax > 0:
            opts.append(
                f"Paying ${result.additional_medicare_tax:,.0f} in Additional Medicare Tax (0.9%). "
                "Consider increasing pre-tax retirement contributions."
            )
        
        # Retirement contributions
        for w2 in self._w2_data + self._spouse_w2_data:
            if w2.get('box12_d_401k', 0) > 0:
                limit_401k = tc.limit_401k
                if _d(w2.get('box12_d_401k', 0)) < limit_401k:
                    opts.append(
                        f"401(k) contribution below ${limit_401k:,.0f} limit. "
                        "Max it out for tax savings."
                    )
        
        # Charitable giving for high AGI
        if result.agi > Decimal("200000") and self._itemized.get('charity', Decimal("0")) == 0:
            opts.append(
                "Consider charitable giving (cash or appreciated stock) for tax savings. "
                "Donating appreciated stock avoids capital gains tax."
            )
        
        # State tax refund could be taxable next year
        if result.state_refund > Decimal("500") and result.deduction_type == "itemized":
            opts.append(
                f"State tax refund of ${result.state_refund:,.0f} may be taxable "
                "next year if you itemized this year."
            )
        
        result.optimizations = opts
