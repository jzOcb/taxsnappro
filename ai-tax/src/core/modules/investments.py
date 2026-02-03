"""
Investment Income & Capital Gains Module (Schedule B, D, Form 8949)

NOT in IRS Direct File — they only support simple returns.
This module adds support for:
- Schedule B: Interest & Dividend Income (>$1,500 thresholds)
- Schedule D: Capital Gains and Losses
- Form 8949: Sales and Dispositions of Capital Assets
- Qualified Dividends tax calculation (preferential rates)
- Net Investment Income Tax (NIIT) - 3.8% on investment income

2025 Tax Year Constants.
"""

from decimal import Decimal
from typing import Any

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from fact_graph import FactGraph, FactType


# ============================================================
# 2025 Constants
# ============================================================

# Long-term capital gains brackets (MFJ)
LTCG_BRACKETS_MFJ_2025 = [
    (Decimal("96700"), Decimal("0.00")),
    (Decimal("600050"), Decimal("0.15")),
    (Decimal("999999999"), Decimal("0.20")),
]

LTCG_BRACKETS_SINGLE_2025 = [
    (Decimal("48350"), Decimal("0.00")),
    (Decimal("533400"), Decimal("0.15")),
    (Decimal("999999999"), Decimal("0.20")),
]

# NIIT threshold
NIIT_THRESHOLD_MFJ = Decimal("250000")
NIIT_THRESHOLD_SINGLE = Decimal("200000")
NIIT_RATE = Decimal("0.038")

# Schedule B threshold — must file if interest or dividends > $1,500
SCHEDULE_B_THRESHOLD = Decimal("1500")

# Depreciation recapture rate (Section 1250)
DEPRECIATION_RECAPTURE_RATE = Decimal("0.25")

# Capital loss deduction limit
CAPITAL_LOSS_LIMIT = Decimal("3000")  # $3,000 MFJ/Single, $1,500 MFS


# ============================================================
# Helper: Capital Gains Tax Calculator
# ============================================================

def calculate_ltcg_tax(taxable_income: Decimal, ltcg_amount: Decimal,
                       is_mfj: bool = True) -> Decimal:
    """
    Calculate tax on long-term capital gains using preferential rates.
    
    The LTCG tax rate depends on your total taxable income (not just the gains).
    LTCG "stacks on top" of ordinary income for bracket purposes.
    """
    brackets = LTCG_BRACKETS_MFJ_2025 if is_mfj else LTCG_BRACKETS_SINGLE_2025
    
    # Ordinary income fills brackets first
    ordinary_income = taxable_income - ltcg_amount
    if ordinary_income < Decimal("0"):
        ordinary_income = Decimal("0")
    
    tax = Decimal("0")
    remaining_gains = ltcg_amount
    income_so_far = ordinary_income
    
    for bracket_top, rate in brackets:
        if remaining_gains <= 0:
            break
        
        # How much room is left in this bracket?
        room = max(bracket_top - income_so_far, Decimal("0"))
        gains_in_bracket = min(remaining_gains, room)
        
        tax += gains_in_bracket * rate
        remaining_gains -= gains_in_bracket
        income_so_far += gains_in_bracket
    
    return tax.quantize(Decimal("0.01"))


# ============================================================
# Module: Schedule B (Interest & Dividends)
# ============================================================

def build_schedule_b_module(graph: FactGraph):
    """Register Schedule B facts for interest and dividend reporting."""
    module = "scheduleB"
    
    # --- 1099-INT support (multiple accounts) ---
    for i in range(5):  # Support up to 5 interest sources
        prefix = f"/interest/{i}"
        graph.register_writable(f"{prefix}/payerName", f"Interest Payer {i+1} Name", FactType.STRING, module)
        graph.register_writable(f"{prefix}/amount", f"Interest Income {i+1} (Box 1)", FactType.DECIMAL, module, export_mef=True)
        graph.register_writable(f"{prefix}/earlyWithdrawalPenalty", f"Early Withdrawal Penalty {i+1} (Box 2)", FactType.DECIMAL, module)
        graph.register_writable(f"{prefix}/usSavingsBondInterest", f"US Savings Bond Interest {i+1} (Box 3)", FactType.DECIMAL, module)
        graph.register_writable(f"{prefix}/taxExemptInterest", f"Tax-Exempt Interest {i+1} (Box 8)", FactType.DECIMAL, module)
        graph.register_writable(f"{prefix}/federalTaxWithheld", f"Federal Tax Withheld {i+1} (Box 4)", FactType.DECIMAL, module)

    # --- 1099-DIV support (multiple accounts) ---
    for i in range(5):  # Support up to 5 dividend sources
        prefix = f"/dividends/{i}"
        graph.register_writable(f"{prefix}/payerName", f"Dividend Payer {i+1} Name", FactType.STRING, module)
        graph.register_writable(f"{prefix}/ordinaryDividends", f"Ordinary Dividends {i+1} (Box 1a)", FactType.DECIMAL, module, export_mef=True)
        graph.register_writable(f"{prefix}/qualifiedDividends", f"Qualified Dividends {i+1} (Box 1b)", FactType.DECIMAL, module, export_mef=True)
        graph.register_writable(f"{prefix}/totalCapitalGain", f"Total Capital Gain Dist {i+1} (Box 2a)", FactType.DECIMAL, module)
        graph.register_writable(f"{prefix}/foreignTaxPaid", f"Foreign Tax Paid {i+1} (Box 7)", FactType.DECIMAL, module)
        graph.register_writable(f"{prefix}/exemptInterestDividends", f"Exempt-Interest Dividends {i+1} (Box 12)", FactType.DECIMAL, module)
        graph.register_writable(f"{prefix}/federalTaxWithheld", f"Federal Tax Withheld {i+1} (Box 4)", FactType.DECIMAL, module)

    # --- Aggregated totals ---
    interest_paths = [f"/interest/{i}/amount" for i in range(5)]
    graph.register_derived(
        "/totalInterest", "Total Interest Income", FactType.DECIMAL, module,
        dependencies=interest_paths,
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        export_mef=True,
    )
    
    tax_exempt_paths = [f"/interest/{i}/taxExemptInterest" for i in range(5)]
    graph.register_derived(
        "/totalTaxExemptInterest", "Total Tax-Exempt Interest", FactType.DECIMAL, module,
        dependencies=tax_exempt_paths,
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        export_mef=True,
    )
    
    ordinary_div_paths = [f"/dividends/{i}/ordinaryDividends" for i in range(5)]
    graph.register_derived(
        "/totalOrdinaryDividends", "Total Ordinary Dividends", FactType.DECIMAL, module,
        dependencies=ordinary_div_paths,
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        export_mef=True,
    )
    
    qualified_div_paths = [f"/dividends/{i}/qualifiedDividends" for i in range(5)]
    graph.register_derived(
        "/totalQualifiedDividends", "Total Qualified Dividends", FactType.DECIMAL, module,
        dependencies=qualified_div_paths,
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        export_mef=True,
    )
    
    cap_gain_dist_paths = [f"/dividends/{i}/totalCapitalGain" for i in range(5)]
    graph.register_derived(
        "/totalCapitalGainDistributions", "Total Capital Gain Distributions", FactType.DECIMAL, module,
        dependencies=cap_gain_dist_paths,
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
    )
    
    foreign_tax_paths = [f"/dividends/{i}/foreignTaxPaid" for i in range(5)]
    graph.register_derived(
        "/totalForeignTaxPaid", "Total Foreign Tax Paid (Dividends)", FactType.DECIMAL, module,
        dependencies=foreign_tax_paths,
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
    )
    
    # Schedule B required?
    graph.register_derived(
        "/requiresScheduleB", "Requires Schedule B", FactType.BOOLEAN, module,
        dependencies=["/totalInterest", "/totalOrdinaryDividends"],
        derive_fn=lambda deps: (
            (deps.get("/totalInterest") or Decimal("0")) > SCHEDULE_B_THRESHOLD or
            (deps.get("/totalOrdinaryDividends") or Decimal("0")) > SCHEDULE_B_THRESHOLD
        ),
    )


# ============================================================
# Module: Schedule D (Capital Gains/Losses) + Form 8949
# ============================================================

def build_schedule_d_module(graph: FactGraph):
    """Register Schedule D and Form 8949 facts."""
    module = "scheduleD"
    
    # --- Form 8949 transactions (support up to 20) ---
    for i in range(20):
        prefix = f"/transactions/{i}"
        graph.register_writable(f"{prefix}/description", f"Transaction {i+1} Description", FactType.STRING, module)
        graph.register_writable(f"{prefix}/dateAcquired", f"Date Acquired {i+1}", FactType.DATE, module)
        graph.register_writable(f"{prefix}/dateSold", f"Date Sold {i+1}", FactType.DATE, module)
        graph.register_writable(f"{prefix}/proceeds", f"Proceeds {i+1} (1099-B Box 1d)", FactType.DECIMAL, module, export_mef=True)
        graph.register_writable(f"{prefix}/costBasis", f"Cost Basis {i+1} (1099-B Box 1e)", FactType.DECIMAL, module, export_mef=True)
        graph.register_writable(f"{prefix}/washSaleAdjustment", f"Wash Sale Adj {i+1} (Box 1g)", FactType.DECIMAL, module)
        graph.register_writable(f"{prefix}/isShortTerm", f"Is Short Term {i+1}", FactType.BOOLEAN, module)
        graph.register_writable(f"{prefix}/basisReportedToIrs", f"Basis Reported to IRS {i+1}", FactType.BOOLEAN, module)
        
        # Per-transaction gain/loss
        graph.register_derived(
            f"{prefix}/gainLoss", f"Gain/Loss {i+1}", FactType.DECIMAL, module,
            dependencies=[f"{prefix}/proceeds", f"{prefix}/costBasis", f"{prefix}/washSaleAdjustment"],
            derive_fn=lambda deps, p=prefix: (
                (deps.get(f"{p}/proceeds") or Decimal("0")) -
                (deps.get(f"{p}/costBasis") or Decimal("0")) +
                (deps.get(f"{p}/washSaleAdjustment") or Decimal("0"))
            ),
        )
    
    # --- Broker summary input (alternative to individual transactions) ---
    graph.register_writable("/brokerSummary/shortTermProceeds", "Total ST Proceeds", FactType.DECIMAL, module)
    graph.register_writable("/brokerSummary/shortTermBasis", "Total ST Cost Basis", FactType.DECIMAL, module)
    graph.register_writable("/brokerSummary/shortTermWashSales", "Total ST Wash Sale Adj", FactType.DECIMAL, module)
    graph.register_writable("/brokerSummary/longTermProceeds", "Total LT Proceeds", FactType.DECIMAL, module)
    graph.register_writable("/brokerSummary/longTermBasis", "Total LT Cost Basis", FactType.DECIMAL, module)
    graph.register_writable("/brokerSummary/longTermWashSales", "Total LT Wash Sale Adj", FactType.DECIMAL, module)
    
    # Carryover loss from prior years
    graph.register_writable("/capitalLossCarryover", "Capital Loss Carryover from Prior Year", FactType.DECIMAL, module)
    graph.register_writable("/capitalLossCarryoverShortTerm", "ST Capital Loss Carryover", FactType.DECIMAL, module)
    graph.register_writable("/capitalLossCarryoverLongTerm", "LT Capital Loss Carryover", FactType.DECIMAL, module)
    
    # --- Aggregated gains/losses ---
    graph.register_derived(
        "/netShortTermGain", "Net Short-Term Capital Gain/Loss", FactType.DECIMAL, module,
        dependencies=[
            "/brokerSummary/shortTermProceeds", "/brokerSummary/shortTermBasis",
            "/brokerSummary/shortTermWashSales", "/capitalLossCarryoverShortTerm",
        ],
        derive_fn=lambda deps: (
            (deps.get("/brokerSummary/shortTermProceeds") or Decimal("0")) -
            (deps.get("/brokerSummary/shortTermBasis") or Decimal("0")) +
            (deps.get("/brokerSummary/shortTermWashSales") or Decimal("0")) +
            (deps.get("/capitalLossCarryoverShortTerm") or Decimal("0"))  # Carryover is negative
        ),
        export_mef=True,
    )
    
    graph.register_derived(
        "/netLongTermGain", "Net Long-Term Capital Gain/Loss", FactType.DECIMAL, module,
        dependencies=[
            "/brokerSummary/longTermProceeds", "/brokerSummary/longTermBasis",
            "/brokerSummary/longTermWashSales", "/capitalLossCarryoverLongTerm",
            "/totalCapitalGainDistributions",
        ],
        derive_fn=lambda deps: (
            (deps.get("/brokerSummary/longTermProceeds") or Decimal("0")) -
            (deps.get("/brokerSummary/longTermBasis") or Decimal("0")) +
            (deps.get("/brokerSummary/longTermWashSales") or Decimal("0")) +
            (deps.get("/capitalLossCarryoverLongTerm") or Decimal("0")) +
            (deps.get("/totalCapitalGainDistributions") or Decimal("0"))
        ),
        export_mef=True,
    )
    
    # Net capital gain/loss (Schedule D line 16)
    graph.register_derived(
        "/netCapitalGain", "Net Capital Gain/Loss", FactType.DECIMAL, module,
        dependencies=["/netShortTermGain", "/netLongTermGain"],
        derive_fn=lambda deps: (
            (deps.get("/netShortTermGain") or Decimal("0")) +
            (deps.get("/netLongTermGain") or Decimal("0"))
        ),
        export_mef=True,
    )
    
    # Capital loss deduction (limited to $3,000)
    graph.register_derived(
        "/capitalLossDeduction", "Capital Loss Deduction (max $3,000)", FactType.DECIMAL, module,
        dependencies=["/netCapitalGain"],
        derive_fn=lambda deps: (
            max(deps.get("/netCapitalGain") or Decimal("0"), -CAPITAL_LOSS_LIMIT)
            if (deps.get("/netCapitalGain") or Decimal("0")) < Decimal("0")
            else deps.get("/netCapitalGain") or Decimal("0")
        ),
        export_mef=True,
    )
    
    # New carryover to next year
    graph.register_derived(
        "/newCapitalLossCarryover", "Capital Loss Carryover to Next Year", FactType.DECIMAL, module,
        dependencies=["/netCapitalGain"],
        derive_fn=lambda deps: (
            min((deps.get("/netCapitalGain") or Decimal("0")) + CAPITAL_LOSS_LIMIT, Decimal("0"))
            if (deps.get("/netCapitalGain") or Decimal("0")) < -CAPITAL_LOSS_LIMIT
            else Decimal("0")
        ),
    )


# ============================================================
# Module: Schedule E (Rental Property)
# ============================================================

def build_schedule_e_module(graph: FactGraph):
    """Register Schedule E facts for rental real estate income."""
    module = "scheduleE"
    
    # Support up to 3 rental properties
    for i in range(3):
        prefix = f"/rental/{i}"
        
        # Property info
        graph.register_writable(f"{prefix}/address", f"Rental Property {i+1} Address", FactType.STRING, module)
        graph.register_writable(f"{prefix}/propertyType", f"Property Type {i+1}", FactType.ENUM, module)
        graph.register_writable(f"{prefix}/daysRented", f"Days Rented {i+1}", FactType.INTEGER, module)
        graph.register_writable(f"{prefix}/daysPersonalUse", f"Days Personal Use {i+1}", FactType.INTEGER, module)
        
        # Income
        graph.register_writable(f"{prefix}/rentsReceived", f"Rents Received {i+1}", FactType.DECIMAL, module, export_mef=True)
        
        # Expenses (Schedule E Part I lines 5-19)
        expenses = [
            ("advertising", "Advertising"),
            ("autoTravel", "Auto and Travel"),
            ("cleaning", "Cleaning and Maintenance"),
            ("commissions", "Commissions"),
            ("insurance", "Insurance"),
            ("legal", "Legal and Professional Fees"),
            ("management", "Management Fees"),
            ("mortgageInterest", "Mortgage Interest"),
            ("otherInterest", "Other Interest"),
            ("repairs", "Repairs"),
            ("supplies", "Supplies"),
            ("taxes", "Property Taxes"),
            ("utilities", "Utilities"),
            ("depreciation", "Depreciation"),
            ("other", "Other Expenses"),
        ]
        
        expense_paths = []
        for key, name in expenses:
            path = f"{prefix}/expenses/{key}"
            graph.register_writable(path, f"{name} {i+1}", FactType.DECIMAL, module, export_mef=True)
            expense_paths.append(path)
        
        # Total expenses
        graph.register_derived(
            f"{prefix}/totalExpenses", f"Total Expenses {i+1}", FactType.DECIMAL, module,
            dependencies=expense_paths,
            derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        )
        
        # Net rental income/loss
        graph.register_derived(
            f"{prefix}/netIncome", f"Net Rental Income/Loss {i+1}", FactType.DECIMAL, module,
            dependencies=[f"{prefix}/rentsReceived", f"{prefix}/totalExpenses"],
            derive_fn=lambda deps, p=prefix: (
                (deps.get(f"{p}/rentsReceived") or Decimal("0")) -
                (deps.get(f"{p}/totalExpenses") or Decimal("0"))
            ),
            export_mef=True,
        )
        
        # --- Depreciation calculator ---
        graph.register_writable(f"{prefix}/purchasePrice", f"Purchase Price {i+1}", FactType.DECIMAL, module)
        graph.register_writable(f"{prefix}/landValue", f"Land Value {i+1}", FactType.DECIMAL, module)
        graph.register_writable(f"{prefix}/purchaseDate", f"Purchase Date {i+1}", FactType.DATE, module)
        graph.register_writable(f"{prefix}/priorDepreciation", f"Prior Depreciation Taken {i+1}", FactType.DECIMAL, module)
        
        graph.register_derived(
            f"{prefix}/depreciableBasis", f"Depreciable Basis {i+1}", FactType.DECIMAL, module,
            dependencies=[f"{prefix}/purchasePrice", f"{prefix}/landValue"],
            derive_fn=lambda deps, p=prefix: (
                (deps.get(f"{p}/purchasePrice") or Decimal("0")) -
                (deps.get(f"{p}/landValue") or Decimal("0"))
            ),
        )
        
        graph.register_derived(
            f"{prefix}/annualDepreciation", f"Annual Depreciation {i+1}", FactType.DECIMAL, module,
            dependencies=[f"{prefix}/depreciableBasis"],
            derive_fn=lambda deps, p=prefix: (
                ((deps.get(f"{p}/depreciableBasis") or Decimal("0")) / Decimal("27.5")).quantize(Decimal("0.01"))
            ),
            description="Straight-line depreciation over 27.5 years for residential rental property",
        )
    
    # --- Aggregate rental income ---
    net_paths = [f"/rental/{i}/netIncome" for i in range(3)]
    graph.register_derived(
        "/totalNetRentalIncome", "Total Net Rental Income/Loss (All Properties)", FactType.DECIMAL, module,
        dependencies=net_paths,
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        export_mef=True,
    )
    
    # Passive Activity Loss Rules (IRC §469)
    # At AGI > $150K, the $25K allowance is fully phased out
    graph.register_writable("/isRealEstateProfessional", "Qualifies as Real Estate Professional", FactType.BOOLEAN, module)
    
    graph.register_derived(
        "/rentalLossAllowance", "Rental Loss Allowance", FactType.DECIMAL, module,
        dependencies=["/totalNetRentalIncome", "/isRealEstateProfessional"],
        derive_fn=lambda deps: (
            # If REPS, all losses are deductible (non-passive)
            deps.get("/totalNetRentalIncome") or Decimal("0")
            if deps.get("/isRealEstateProfessional")
            # If net income is positive, no limitation
            else deps.get("/totalNetRentalIncome") or Decimal("0")
            if (deps.get("/totalNetRentalIncome") or Decimal("0")) >= Decimal("0")
            # If loss and not REPS: at $500K+ AGI, loss is fully suspended
            # (simplified — full logic would need AGI from tax calc module)
            else Decimal("0")  # Suspended for high-income non-REPS
        ),
        description="For AGI > $150K non-REPS: rental losses are suspended (passive activity rules)",
    )


# ============================================================
# Module: NIIT (Net Investment Income Tax) — Form 8960
# ============================================================

def build_niit_module(graph: FactGraph):
    """Register NIIT facts — 3.8% on investment income for high earners."""
    module = "niit"
    
    # Net investment income components
    graph.register_derived(
        "/netInvestmentIncome", "Net Investment Income", FactType.DECIMAL, module,
        dependencies=[
            "/totalInterest", "/totalOrdinaryDividends",
            "/netCapitalGain", "/totalNetRentalIncome",
        ],
        derive_fn=lambda deps: max(
            sum((v or Decimal("0")) for v in deps.values()),
            Decimal("0")
        ),
        export_mef=True,
    )
    
    # NIIT calculation (simplified — uses isFilingStatusMFJ dependency)
    # Full implementation would need AGI from tax calc module
    graph.register_writable("/niit/agi", "AGI for NIIT Calculation", FactType.DECIMAL, module,
                           description="This should be linked to the main AGI derived fact")
    graph.register_writable("/niit/isMFJ", "Filing MFJ (for NIIT threshold)", FactType.BOOLEAN, module)
    
    graph.register_derived(
        "/niitTax", "Net Investment Income Tax", FactType.DECIMAL, module,
        dependencies=["/netInvestmentIncome", "/niit/agi", "/niit/isMFJ"],
        derive_fn=lambda deps: _calc_niit(
            deps.get("/netInvestmentIncome") or Decimal("0"),
            deps.get("/niit/agi") or Decimal("0"),
            deps.get("/niit/isMFJ", True),
        ),
        export_mef=True,
    )


def _calc_niit(nii: Decimal, agi: Decimal, is_mfj: bool) -> Decimal:
    """Calculate Net Investment Income Tax (Form 8960)."""
    threshold = NIIT_THRESHOLD_MFJ if is_mfj else NIIT_THRESHOLD_SINGLE
    
    if agi <= threshold:
        return Decimal("0")
    
    excess_agi = agi - threshold
    taxable_nii = min(nii, excess_agi)
    
    return (taxable_nii * NIIT_RATE).quantize(Decimal("0.01"))


# ============================================================
# Module: Itemized Deductions (Schedule A)
# ============================================================

def build_schedule_a_module(graph: FactGraph):
    """Register Schedule A (Itemized Deductions) facts."""
    module = "scheduleA"
    
    SALT_CAP = Decimal("10000")
    
    # Medical expenses
    graph.register_writable("/itemized/medicalExpenses", "Medical & Dental Expenses", FactType.DECIMAL, module)
    graph.register_writable("/itemized/agi_for_medical", "AGI for Medical Threshold", FactType.DECIMAL, module)
    
    graph.register_derived(
        "/itemized/medicalDeduction", "Medical Deduction (exceeding 7.5% AGI)", FactType.DECIMAL, module,
        dependencies=["/itemized/medicalExpenses", "/itemized/agi_for_medical"],
        derive_fn=lambda deps: max(
            (deps.get("/itemized/medicalExpenses") or Decimal("0")) -
            (deps.get("/itemized/agi_for_medical") or Decimal("0")) * Decimal("0.075"),
            Decimal("0")
        ).quantize(Decimal("0.01")),
        export_mef=True,
    )
    
    # SALT (State and Local Taxes) — capped at $10,000
    graph.register_writable("/itemized/stateIncomeTax", "State/Local Income Tax Paid", FactType.DECIMAL, module)
    graph.register_writable("/itemized/realEstateTax", "Real Estate Taxes (Primary Home)", FactType.DECIMAL, module)
    graph.register_writable("/itemized/personalPropertyTax", "Personal Property Tax", FactType.DECIMAL, module)
    
    graph.register_derived(
        "/itemized/saltDeduction", "SALT Deduction (capped at $10,000)", FactType.DECIMAL, module,
        dependencies=["/itemized/stateIncomeTax", "/itemized/realEstateTax", "/itemized/personalPropertyTax"],
        derive_fn=lambda deps: min(
            sum((v or Decimal("0")) for v in deps.values()),
            SALT_CAP
        ),
        export_mef=True,
        description="State and Local Tax deduction, capped at $10,000 under TCJA",
    )
    
    # Interest deduction
    graph.register_writable("/itemized/homeMortgageInterest", "Home Mortgage Interest (1098 Box 1)", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable("/itemized/mortgagePoints", "Mortgage Points Paid", FactType.DECIMAL, module)
    graph.register_writable("/itemized/investmentInterest", "Investment Interest Expense", FactType.DECIMAL, module)
    
    graph.register_derived(
        "/itemized/interestDeduction", "Total Interest Deduction", FactType.DECIMAL, module,
        dependencies=["/itemized/homeMortgageInterest", "/itemized/mortgagePoints", "/itemized/investmentInterest"],
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        export_mef=True,
    )
    
    # Charitable contributions
    graph.register_writable("/itemized/charityCash", "Cash Charitable Contributions", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable("/itemized/charityNoncash", "Non-Cash Charitable Contributions", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable("/itemized/charityCarryover", "Charitable Contribution Carryover", FactType.DECIMAL, module)
    
    graph.register_derived(
        "/itemized/charityDeduction", "Total Charitable Deduction", FactType.DECIMAL, module,
        dependencies=["/itemized/charityCash", "/itemized/charityNoncash", "/itemized/charityCarryover"],
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        export_mef=True,
    )
    
    # Casualty/theft losses (only federally declared disasters)
    graph.register_writable("/itemized/casualtyLoss", "Casualty/Theft Losses", FactType.DECIMAL, module)
    
    # Other itemized deductions
    graph.register_writable("/itemized/otherDeductions", "Other Itemized Deductions", FactType.DECIMAL, module)
    
    # --- Total itemized deductions ---
    graph.register_derived(
        "/totalItemizedDeductions", "Total Itemized Deductions", FactType.DECIMAL, module,
        dependencies=[
            "/itemized/medicalDeduction", "/itemized/saltDeduction",
            "/itemized/interestDeduction", "/itemized/charityDeduction",
            "/itemized/casualtyLoss", "/itemized/otherDeductions",
        ],
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        export_mef=True,
    )
    
    # Itemize vs Standard?
    graph.register_writable("/standardDeductionAmount", "Standard Deduction Amount", FactType.DECIMAL, module,
                           description="Linked from tax calc module")
    
    graph.register_derived(
        "/shouldItemize", "Should Itemize (vs Standard)", FactType.BOOLEAN, module,
        dependencies=["/totalItemizedDeductions", "/standardDeductionAmount"],
        derive_fn=lambda deps: (
            (deps.get("/totalItemizedDeductions") or Decimal("0")) >
            (deps.get("/standardDeductionAmount") or Decimal("30000"))
        ),
    )
    
    graph.register_derived(
        "/deductionUsed", "Deduction Used (higher of standard or itemized)", FactType.DECIMAL, module,
        dependencies=["/totalItemizedDeductions", "/standardDeductionAmount"],
        derive_fn=lambda deps: max(
            deps.get("/totalItemizedDeductions") or Decimal("0"),
            deps.get("/standardDeductionAmount") or Decimal("30000")
        ),
        export_mef=True,
    )


# ============================================================
# Register All Investment Modules
# ============================================================

def build_all_investment_modules(graph: FactGraph):
    """Register all investment-related modules in the graph."""
    build_schedule_b_module(graph)
    build_schedule_d_module(graph)
    build_schedule_e_module(graph)
    build_niit_module(graph)
    build_schedule_a_module(graph)
