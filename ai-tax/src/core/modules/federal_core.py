"""
Federal Core Tax Module — Python port of IRS Direct File XML fact dictionaries.

Ported from:
  - taxCalculations.xml  (AGI, taxable income, brackets, total tax, payments)
  - income.xml           (total income aggregation, employer income)
  - interest.xml         (1099-INT interest income, Schedule B thresholds, NIIT thresholds)
  - standardDeduction.xml (standard deduction with age/blind adjustments)
  - filingStatus.xml     (filing status derived boolean flags)

Tax Year: 2025  (Rev. Proc. 2024-40 inflation adjustments)

Reference: github.com/IRS-Public/direct-file/
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from core.fact_graph import FactGraph, FactType
except ImportError:
    # Support running from project root or from src/
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from fact_graph import FactGraph, FactType

# ============================================================
# 2025 Tax Year Constants (Rev. Proc. 2024-40)
# ============================================================

TAX_YEAR = 2025

# --- Standard Deductions ---
STD_DEDUCTION_SINGLE = Decimal("15000")
STD_DEDUCTION_MFS = Decimal("15000")
STD_DEDUCTION_MFJ = Decimal("30000")
STD_DEDUCTION_QSS = Decimal("30000")
STD_DEDUCTION_HOH = Decimal("22500")

# Additional standard deduction per qualifying item (age 65+ or blind)
ADDITIONAL_STD_DEDUCTION_SINGLE_HOH = Decimal("2000")
ADDITIONAL_STD_DEDUCTION_MFJ_MFS_QSS = Decimal("1600")

# Dependent standard deduction floor and earned income adder
DEPENDENT_STD_DEDUCTION_FLOOR = Decimal("1350")
DEPENDENT_EARNED_INCOME_ADDER = Decimal("450")

# --- Federal Income Tax Brackets ---
# Format: list of (upper_bound, rate, base_tax, bracket_start)
# upper_bound=None means no limit (top bracket)

BRACKETS_SINGLE = [
    (Decimal("11925"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
    (Decimal("48475"),  Decimal("0.12"), Decimal("1192.50"),   Decimal("11925")),
    (Decimal("103350"), Decimal("0.22"), Decimal("5578.50"),   Decimal("48475")),
    (Decimal("197300"), Decimal("0.24"), Decimal("17651.50"),  Decimal("103350")),
    (Decimal("250525"), Decimal("0.32"), Decimal("40199.50"),  Decimal("197300")),
    (Decimal("626350"), Decimal("0.35"), Decimal("57231.50"),  Decimal("250525")),
    (None,              Decimal("0.37"), Decimal("188769.75"), Decimal("626350")),
]

BRACKETS_MFJ_QSS = [
    (Decimal("23850"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
    (Decimal("96950"),  Decimal("0.12"), Decimal("2385"),      Decimal("23850")),
    (Decimal("206700"), Decimal("0.22"), Decimal("11157"),     Decimal("96950")),
    (Decimal("394600"), Decimal("0.24"), Decimal("35302"),     Decimal("206700")),
    (Decimal("501050"), Decimal("0.32"), Decimal("80398"),     Decimal("394600")),
    (Decimal("751600"), Decimal("0.35"), Decimal("114462"),    Decimal("501050")),
    (None,              Decimal("0.37"), Decimal("202154.50"), Decimal("751600")),
]

BRACKETS_HOH = [
    (Decimal("17000"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
    (Decimal("64850"),  Decimal("0.12"), Decimal("1700"),      Decimal("17000")),
    (Decimal("103350"), Decimal("0.22"), Decimal("7442"),      Decimal("64850")),
    (Decimal("197300"), Decimal("0.24"), Decimal("15912"),     Decimal("103350")),
    (Decimal("250500"), Decimal("0.32"), Decimal("38460"),     Decimal("197300")),
    (Decimal("626350"), Decimal("0.35"), Decimal("55484"),     Decimal("250500")),
    (None,              Decimal("0.37"), Decimal("187031.50"), Decimal("626350")),
]

BRACKETS_MFS = [
    (Decimal("11925"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
    (Decimal("48475"),  Decimal("0.12"), Decimal("1192.50"),   Decimal("11925")),
    (Decimal("103350"), Decimal("0.22"), Decimal("5578.50"),   Decimal("48475")),
    (Decimal("197300"), Decimal("0.24"), Decimal("17651.50"),  Decimal("103350")),
    (Decimal("250525"), Decimal("0.32"), Decimal("40199.50"),  Decimal("197300")),
    (Decimal("375800"), Decimal("0.35"), Decimal("57231.50"),  Decimal("250525")),
    (None,              Decimal("0.37"), Decimal("101077.75"), Decimal("375800")),
]

# --- Additional Medicare Tax (Form 8959) ---
ADDITIONAL_MEDICARE_TAX_RATE = Decimal("0.009")  # 0.9%
MEDICARE_TAX_THRESHOLD_MFJ = Decimal("250000")
MEDICARE_TAX_THRESHOLD_MFS = Decimal("125000")
MEDICARE_TAX_THRESHOLD_SINGLE_HOH_QSS = Decimal("200000")

# --- Net Investment Income Tax (Form 8960) ---
NIIT_RATE = Decimal("0.038")  # 3.8%
NIIT_THRESHOLD_MFJ_QSS = Decimal("250000")
NIIT_THRESHOLD_MFS = Decimal("125000")
NIIT_THRESHOLD_SINGLE_HOH = Decimal("200000")

# --- Schedule B threshold ---
SCHEDULE_B_INTEREST_THRESHOLD = Decimal("1500")


# ============================================================
# Helpers
# ============================================================

def _d(val: Any) -> Decimal:
    """Safely coerce to Decimal, defaulting to 0."""
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _round(val: Decimal) -> Decimal:
    """Round to nearest dollar (matches IRS rounding: .50+ rounds up)."""
    return val.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _compute_bracket_tax(taxable_income: Decimal, brackets: list) -> Decimal:
    """
    Compute federal income tax from bracket table.

    Ports the <Switch>/<Case> bracket logic from taxCalculations.xml.
    For income < $100K the IRS uses tax tables with midpoint rounding;
    for income >= $100K the tax computation worksheet uses exact amounts.
    We implement the exact computation for all amounts (matches the worksheet).
    """
    if taxable_income <= 0:
        return Decimal("0")

    for upper, rate, base_tax, bracket_start in brackets:
        if upper is None or taxable_income <= upper:
            tax = base_tax + rate * (taxable_income - bracket_start)
            return _round(tax)

    # Should never reach here
    return Decimal("0")


def _get_rounded_taxable_income(taxable_income: Decimal) -> Decimal:
    """
    Port of /roundedTaxableIncome from taxCalculations.xml.

    For income < $100K, the IRS tax tables use midpoint rounding.
    For income >= $100K, the exact amount is used.
    """
    ti = _d(taxable_income)
    if ti <= 0:
        return Decimal("0")
    if ti < 5:
        return Decimal("2.50")
    if ti < 15:
        return Decimal("10")
    if ti < 25:
        return Decimal("20")
    if ti < 3000:
        # $25 increments, midpoint
        step = int(ti // 25) * 25
        return Decimal(str(step)) + Decimal("12.50")
    if ti < 100000:
        # $50 increments, midpoint
        step = int(ti // 50) * 50
        return Decimal(str(step)) + Decimal("25")
    # >= $100K: use exact amount
    return ti


# ============================================================
# Module: Filing Status
# ============================================================

def build_filing_status_module(graph: FactGraph):
    """
    Register filing status facts.

    Ports filingStatus.xml: /filingStatus (writable enum) and
    derived boolean flags /isFilingStatusMFJ, /isFilingStatusSingle, etc.
    """
    module = "filingStatus"

    # The user-selected filing status
    graph.register_writable(
        "/filingStatus", "Filing Status", FactType.ENUM, module,
        description="Filing status: single, married_filing_jointly, married_filing_separately, "
                    "head_of_household, qualifying_surviving_spouse",
        export_mef=True,
    )

    # Derived boolean flags — mirrors XML's Equal comparisons
    graph.register_derived(
        "/isFilingStatusSingle", "Is Single", FactType.BOOLEAN, module,
        dependencies=["/filingStatus"],
        derive_fn=lambda d: d["/filingStatus"] == "single",
        export_downstream=True,
    )

    graph.register_derived(
        "/isFilingStatusMFJ", "Is MFJ", FactType.BOOLEAN, module,
        dependencies=["/filingStatus"],
        derive_fn=lambda d: d["/filingStatus"] == "married_filing_jointly",
        export_downstream=True, export_mef=True,
    )

    graph.register_derived(
        "/isFilingStatusMFS", "Is MFS", FactType.BOOLEAN, module,
        dependencies=["/filingStatus"],
        derive_fn=lambda d: d["/filingStatus"] == "married_filing_separately",
        export_downstream=True,
    )

    graph.register_derived(
        "/isFilingStatusHOH", "Is HOH", FactType.BOOLEAN, module,
        dependencies=["/filingStatus"],
        derive_fn=lambda d: d["/filingStatus"] == "head_of_household",
        export_downstream=True,
    )

    graph.register_derived(
        "/isFilingStatusQSS", "Is QSS", FactType.BOOLEAN, module,
        dependencies=["/filingStatus"],
        derive_fn=lambda d: d["/filingStatus"] == "qualifying_surviving_spouse",
        export_downstream=True,
    )

    # Exemption count: 2 for MFJ, 1 otherwise  (from taxCalculations.xml)
    graph.register_derived(
        "/totalExemptPrimaryAndSpouseCount", "Primary+Spouse Exemption Count",
        FactType.INTEGER, module,
        dependencies=["/isFilingStatusMFJ"],
        derive_fn=lambda d: 2 if d.get("/isFilingStatusMFJ") else 1,
        export_mef=True,
    )


# ============================================================
# Module: Standard Deduction
# ============================================================

def build_standard_deduction_module(graph: FactGraph):
    """
    Register standard deduction facts.

    Ports standardDeduction.xml with 2025 amounts:
    - Base deduction by filing status
    - Additional deduction for age 65+ and/or blindness
    - Dependent minimum standard deduction
    """
    module = "standardDeduction"

    # --- Writable inputs for age/blind adjustments ---
    graph.register_writable(
        "/filers/primary/isBlind", "Primary Filer Is Blind",
        FactType.BOOLEAN, module,
    )
    graph.register_writable(
        "/filers/primary/is65OrOlder", "Primary Filer Is 65+",
        FactType.BOOLEAN, module,
    )
    graph.register_writable(
        "/filers/secondary/isBlind", "Spouse Is Blind",
        FactType.BOOLEAN, module,
    )
    graph.register_writable(
        "/filers/secondary/is65OrOlder", "Spouse Is 65+",
        FactType.BOOLEAN, module,
    )
    graph.register_writable(
        "/canBeClaimedAsDependent", "Can Be Claimed as Dependent",
        FactType.BOOLEAN, module,
        description="Whether the filer can be claimed as a dependent on another return",
    )

    # --- Filing-status base deduction ---
    # Ports /filingStatusStandardDeduction from standardDeduction.xml
    graph.register_derived(
        "/filingStatusStandardDeduction", "Filing Status Standard Deduction",
        FactType.DECIMAL, module,
        dependencies=[
            "/isFilingStatusSingle", "/isFilingStatusMFJ", "/isFilingStatusMFS",
            "/isFilingStatusHOH", "/isFilingStatusQSS",
        ],
        derive_fn=lambda d: (
            STD_DEDUCTION_MFJ if d.get("/isFilingStatusMFJ") or d.get("/isFilingStatusQSS")
            else STD_DEDUCTION_HOH if d.get("/isFilingStatusHOH")
            else STD_DEDUCTION_MFS if d.get("/isFilingStatusMFS")
            else STD_DEDUCTION_SINGLE  # single or fallback
        ),
    )

    # --- Additional deduction multiplier per item ---
    # Ports /additionalStandardDeductionMultiplier
    graph.register_derived(
        "/additionalStandardDeductionMultiplier",
        "Additional Standard Deduction Per Item", FactType.DECIMAL, module,
        dependencies=[
            "/isFilingStatusSingle", "/isFilingStatusHOH",
            "/isFilingStatusMFJ", "/isFilingStatusMFS", "/isFilingStatusQSS",
        ],
        derive_fn=lambda d: (
            ADDITIONAL_STD_DEDUCTION_SINGLE_HOH
            if d.get("/isFilingStatusSingle") or d.get("/isFilingStatusHOH")
            else ADDITIONAL_STD_DEDUCTION_MFJ_MFS_QSS
        ),
    )

    # --- Count of additional items (age + blind for primary + spouse) ---
    # Ports /additionalStandardDeductionItems
    graph.register_derived(
        "/additionalStandardDeductionItems",
        "Additional Standard Deduction Item Count", FactType.INTEGER, module,
        dependencies=[
            "/filers/primary/isBlind", "/filers/primary/is65OrOlder",
            "/filers/secondary/isBlind", "/filers/secondary/is65OrOlder",
            "/isFilingStatusMFJ", "/isFilingStatusQSS", "/isFilingStatusMFS",
        ],
        derive_fn=lambda d: (
            (1 if d.get("/filers/primary/isBlind") else 0)
            + (1 if d.get("/filers/primary/is65OrOlder") else 0)
            + (
                (1 if d.get("/filers/secondary/isBlind") else 0)
                + (1 if d.get("/filers/secondary/is65OrOlder") else 0)
                if d.get("/isFilingStatusMFJ") or d.get("/isFilingStatusQSS") or d.get("/isFilingStatusMFS")
                else 0
            )
        ),
        export_mef=True,
    )

    # --- Additional deduction dollar amount ---
    # Ports /additionalStandardDeduction = items × multiplier
    graph.register_derived(
        "/additionalStandardDeduction", "Additional Standard Deduction Amount",
        FactType.DECIMAL, module,
        dependencies=[
            "/additionalStandardDeductionItems",
            "/additionalStandardDeductionMultiplier",
        ],
        derive_fn=lambda d: (
            Decimal(str(d.get("/additionalStandardDeductionItems", 0)))
            * _d(d.get("/additionalStandardDeductionMultiplier"))
        ),
    )

    # --- Normal standard deduction (base + additional) ---
    # Ports /normalStandardDeduction
    graph.register_derived(
        "/normalStandardDeduction", "Normal Standard Deduction",
        FactType.DECIMAL, module,
        dependencies=["/filingStatusStandardDeduction", "/additionalStandardDeduction"],
        derive_fn=lambda d: (
            _d(d.get("/filingStatusStandardDeduction"))
            + _d(d.get("/additionalStandardDeduction"))
        ),
    )

    # --- Minimum standard deduction for dependents ---
    # Ports /minimumStandardDeduction: max($1,350, earnedIncome + $450) + additional
    graph.register_derived(
        "/minimumStandardDeduction", "Minimum Std Deduction (Dependents)",
        FactType.DECIMAL, module,
        dependencies=["/employerIncomeSubtotal", "/additionalStandardDeduction"],
        derive_fn=lambda d: (
            max(
                DEPENDENT_STD_DEDUCTION_FLOOR,
                _d(d.get("/employerIncomeSubtotal")) + DEPENDENT_EARNED_INCOME_ADDER,
            )
            + _d(d.get("/additionalStandardDeduction"))
        ),
    )

    # --- Final standard deduction ---
    # Ports /standardDeduction: normal if not dependent, min(minimum, normal) if dependent
    graph.register_derived(
        "/standardDeduction", "Standard Deduction", FactType.DECIMAL, module,
        dependencies=[
            "/canBeClaimedAsDependent",
            "/normalStandardDeduction",
            "/minimumStandardDeduction",
        ],
        derive_fn=lambda d: (
            min(
                _d(d.get("/minimumStandardDeduction")),
                _d(d.get("/normalStandardDeduction")),
            )
            if d.get("/canBeClaimedAsDependent")
            else _d(d.get("/normalStandardDeduction"))
        ),
        export_downstream=True,
    )


# ============================================================
# Module: Interest Income (1099-INT)
# ============================================================

def build_interest_income_module(graph: FactGraph):
    """
    Register interest income facts.

    Ports interest.xml: writable 1099-INT fields and derived aggregations.
    Simplified to a single interest report (index 0) — extend with collection
    pattern for multiple 1099-INTs.
    """
    module = "interest"
    prefix = "/interestReports/0"

    # --- Writable 1099-INT fields ---
    graph.register_writable(
        f"{prefix}/payer", "Payer Name", FactType.STRING, module,
        description="Name of institution that paid interest (1099-INT payer)",
    )
    graph.register_writable(
        f"{prefix}/has1099", "Has 1099-INT", FactType.BOOLEAN, module,
        description="Whether there is a Form 1099-INT for this interest",
    )
    graph.register_writable(
        f"{prefix}/1099Amount", "Interest Income (Box 1)", FactType.DECIMAL, module,
        description="Box 1: Interest income on 1099-INT",
        export_mef=True,
    )
    graph.register_writable(
        f"{prefix}/taxExemptInterest", "Tax-Exempt Interest (Box 8)",
        FactType.DECIMAL, module,
        description="Box 8: Tax-exempt interest on 1099-INT",
    )
    graph.register_writable(
        f"{prefix}/taxWithheld", "Federal Tax Withheld (Box 4)",
        FactType.DECIMAL, module,
        description="Box 4: Federal income tax withheld on 1099-INT",
        export_mef=True,
    )
    graph.register_writable(
        f"{prefix}/interestOnGovernmentBonds", "US Savings Bond Interest (Box 3)",
        FactType.DECIMAL, module,
        description="Box 3: Interest on US savings bonds and Treasury obligations",
    )
    graph.register_writable(
        f"{prefix}/no1099Amount", "Interest Without 1099",
        FactType.DECIMAL, module,
        description="Taxable interest not reported on a 1099-INT",
    )

    # --- Derived: taxable interest per report ---
    # Ports /interestReports/*/taxableInterest
    graph.register_derived(
        f"{prefix}/taxableInterest", "Taxable Interest (per report)",
        FactType.DECIMAL, module,
        dependencies=[
            f"{prefix}/has1099", f"{prefix}/1099Amount",
            f"{prefix}/interestOnGovernmentBonds", f"{prefix}/no1099Amount",
        ],
        derive_fn=lambda d: (
            _d(d.get(f"{prefix}/1099Amount"))
            + _d(d.get(f"{prefix}/interestOnGovernmentBonds"))
            if d.get(f"{prefix}/has1099")
            else _d(d.get(f"{prefix}/no1099Amount"))
        ),
    )

    # --- Aggregate: total taxable interest income (Form 1040 line 2b) ---
    # Ports /interestIncome — sum of all interest reports
    graph.register_derived(
        "/interestIncome", "Taxable Interest Income (Line 2b)",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/taxableInterest"],
        derive_fn=lambda d: _round(sum(_d(v) for v in d.values())),
        export_mef=True, export_downstream=True,
    )

    # --- Aggregate: total tax-exempt interest (Form 1040 line 2a) ---
    graph.register_derived(
        "/taxExemptInterest", "Tax-Exempt Interest (Line 2a)",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/taxExemptInterest"],
        derive_fn=lambda d: _round(sum(_d(v) for v in d.values())),
        export_mef=True, export_downstream=True,
    )

    # --- Aggregate: total 1099 withholding from interest ---
    graph.register_derived(
        "/form1099InterestWithholding", "1099-INT Withholding Total",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/taxWithheld"],
        derive_fn=lambda d: _round(sum(_d(v) for v in d.values())),
        export_downstream=True,
    )

    # --- Schedule B required? ---
    # Ports /requiresScheduleB: interest > $1,500
    graph.register_derived(
        "/requiresScheduleB", "Requires Schedule B", FactType.BOOLEAN, module,
        dependencies=["/interestIncome"],
        derive_fn=lambda d: _d(d.get("/interestIncome")) > SCHEDULE_B_INTEREST_THRESHOLD,
        export_mef=True,
    )

    # --- Has interest income ---
    graph.register_derived(
        "/hasInterestIncome", "Has Interest Income", FactType.BOOLEAN, module,
        dependencies=["/interestIncome"],
        derive_fn=lambda d: _d(d.get("/interestIncome")) > 0,
        export_downstream=True,
    )


# ============================================================
# Module: Income Aggregation
# ============================================================

def build_income_module(graph: FactGraph):
    """
    Register income aggregation facts.

    Ports income.xml: employer income subtotal, total income, adjustments, AGI.
    """
    module = "income"

    # --- W-2 wages (writable, simplified to single primary W-2) ---
    # In production, these would be registered by the W-2 module dynamically.
    # We register the aggregate path here.
    graph.register_writable(
        "/totalW2Wages", "Total W-2 Wages (all W-2s)", FactType.DECIMAL, module,
        description="Sum of all W-2 Box 1 wages",
        export_mef=True,
    )

    graph.register_writable(
        "/totalW2MedicareWages", "Total W-2 Medicare Wages", FactType.DECIMAL, module,
        description="Sum of all W-2 Box 5 Medicare wages and tips",
    )

    graph.register_writable(
        "/totalW2MedicareTax", "Total W-2 Medicare Tax Withheld", FactType.DECIMAL, module,
        description="Sum of all W-2 Box 6 Medicare tax withheld",
    )

    # --- Employer income subtotal (Form 1040 line 1z) ---
    # Ports /employerIncomeSubtotal: W-2 wages + tips + household wages + other
    # Simplified: just W-2 wages for now
    graph.register_derived(
        "/employerIncomeSubtotal", "Employer Income Subtotal (Line 1z)",
        FactType.DECIMAL, module,
        dependencies=["/totalW2Wages"],
        derive_fn=lambda d: _round(_d(d.get("/totalW2Wages"))),
        export_mef=True, export_downstream=True,
    )

    # --- Other income sources (writable placeholders) ---
    graph.register_writable(
        "/ordinaryDividends", "Ordinary Dividends (Line 3b)", FactType.DECIMAL, module,
        description="Ordinary dividend income",
        export_mef=True,
    )
    graph.register_writable(
        "/qualifiedDividends", "Qualified Dividends (Line 3a)", FactType.DECIMAL, module,
        description="Qualified dividend income",
    )
    graph.register_writable(
        "/taxableIraDistributions", "Taxable IRA Distributions (Line 4b)",
        FactType.DECIMAL, module,
        description="Taxable IRA distributions",
    )
    graph.register_writable(
        "/taxablePensionsAndAnnuities", "Taxable Pensions (Line 5b)",
        FactType.DECIMAL, module,
        description="Taxable pensions and annuities",
    )
    graph.register_writable(
        "/taxableSocialSecurityBenefits", "Taxable Social Security (Line 6b)",
        FactType.DECIMAL, module,
        description="Taxable social security benefits",
    )
    graph.register_writable(
        "/capitalGainsOrLosses", "Capital Gains/Losses (Line 7)",
        FactType.DECIMAL, module,
        description="Capital gains or losses",
    )
    graph.register_writable(
        "/otherIncome", "Other Income (Line 8)", FactType.DECIMAL, module,
        description="Other income from Schedule 1",
    )
    graph.register_writable(
        "/unemploymentCompensation", "Unemployment Compensation",
        FactType.DECIMAL, module,
        description="Unemployment compensation (1099-G)",
    )

    # --- Total Income (Form 1040 line 9) ---
    # Ports /totalIncome from income.xml
    graph.register_derived(
        "/totalIncome", "Total Income (Line 9)", FactType.DECIMAL, module,
        dependencies=[
            "/employerIncomeSubtotal", "/interestIncome",
            "/ordinaryDividends", "/taxableIraDistributions",
            "/taxablePensionsAndAnnuities", "/taxableSocialSecurityBenefits",
            "/capitalGainsOrLosses", "/otherIncome",
        ],
        derive_fn=lambda d: _round(sum(_d(v) for v in d.values())),
        export_mef=True, export_downstream=True,
    )

    # --- Adjustments to income (Schedule 1 line 26) ---
    # Ports /adjustmentsToIncome — simplified: HSA + educator + student loan
    graph.register_writable(
        "/hsaDeduction", "HSA Deduction", FactType.DECIMAL, module,
        description="Health savings account deduction",
    )
    graph.register_writable(
        "/educatorExpenses", "Educator Expenses", FactType.DECIMAL, module,
        description="Educator expenses adjustment (max $300)",
    )
    graph.register_writable(
        "/studentLoanInterest", "Student Loan Interest", FactType.DECIMAL, module,
        description="Student loan interest deduction (max $2,500)",
    )

    graph.register_derived(
        "/adjustmentsToIncome", "Adjustments to Income (Line 10)",
        FactType.DECIMAL, module,
        dependencies=["/hsaDeduction", "/educatorExpenses", "/studentLoanInterest"],
        derive_fn=lambda d: _round(sum(_d(v) for v in d.values())),
        export_mef=True, export_downstream=True,
    )

    # --- AGI (Form 1040 line 11) ---
    # Ports /agi = totalIncome - adjustmentsToIncome
    graph.register_derived(
        "/agi", "Adjusted Gross Income (Line 11)", FactType.DECIMAL, module,
        dependencies=["/totalIncome", "/adjustmentsToIncome"],
        derive_fn=lambda d: _round(
            _d(d.get("/totalIncome")) - _d(d.get("/adjustmentsToIncome"))
        ),
        export_mef=True, export_downstream=True,
    )

    # --- Total deductions (Line 14) ---
    # Ports /totalDeductions = standardDeduction (only standard supported)
    graph.register_derived(
        "/totalDeductions", "Total Deductions (Line 14)", FactType.DECIMAL, module,
        dependencies=["/standardDeduction"],
        derive_fn=lambda d: _round(_d(d.get("/standardDeduction"))),
        export_mef=True,
    )

    # --- Taxable income (Form 1040 line 15) ---
    # Ports /taxableIncome = max(agi - totalDeductions, 0)
    graph.register_derived(
        "/taxableIncome", "Taxable Income (Line 15)", FactType.DECIMAL, module,
        dependencies=["/agi", "/totalDeductions"],
        derive_fn=lambda d: _round(max(
            _d(d.get("/agi")) - _d(d.get("/totalDeductions")),
            Decimal("0"),
        )),
        export_mef=True,
    )


# ============================================================
# Module: Tax Bracket Calculations
# ============================================================

def build_tax_bracket_module(graph: FactGraph):
    """
    Register tax bracket computation facts.

    Ports /roundedTaxableIncome and /tentativeTaxFromTaxableIncome
    from taxCalculations.xml — the core bracket math for all 5 filing statuses.
    """
    module = "taxBrackets"

    # --- Rounded taxable income (for tax table lookup) ---
    graph.register_derived(
        "/roundedTaxableIncome", "Rounded Taxable Income (Tax Table)",
        FactType.DECIMAL, module,
        dependencies=["/taxableIncome"],
        derive_fn=lambda d: _get_rounded_taxable_income(_d(d.get("/taxableIncome"))),
    )

    # --- Tentative tax from brackets (Form 1040 line 16) ---
    # Ports /tentativeTaxFromTaxableIncome — the big switch/case from XML
    graph.register_derived(
        "/tentativeTaxFromTaxableIncome", "Tax from Brackets (Line 16)",
        FactType.DECIMAL, module,
        dependencies=[
            "/roundedTaxableIncome",
            "/isFilingStatusSingle", "/isFilingStatusMFJ", "/isFilingStatusMFS",
            "/isFilingStatusHOH", "/isFilingStatusQSS",
        ],
        derive_fn=_compute_tentative_tax,
        export_mef=True,
    )


def _compute_tentative_tax(d: dict) -> Decimal:
    """
    Compute tentative tax based on filing status and rounded taxable income.
    Implements the bracket tables from taxCalculations.xml with 2025 constants.
    """
    rti = _d(d.get("/roundedTaxableIncome"))
    if rti <= 0:
        return Decimal("0")

    # Select bracket table based on filing status
    if d.get("/isFilingStatusMFJ") or d.get("/isFilingStatusQSS"):
        brackets = BRACKETS_MFJ_QSS
    elif d.get("/isFilingStatusHOH"):
        brackets = BRACKETS_HOH
    elif d.get("/isFilingStatusMFS"):
        brackets = BRACKETS_MFS
    else:
        # Single or fallback
        brackets = BRACKETS_SINGLE

    return _compute_bracket_tax(rti, brackets)


# ============================================================
# Module: Tax Calculation (total tax, credits, payments)
# ============================================================

def build_tax_calculation_module(graph: FactGraph):
    """
    Register core tax calculation facts.

    Ports the remaining taxCalculations.xml facts:
    - Total tentative tax (line 18)
    - Non-refundable credits (line 21, simplified)
    - Tax less credits (line 22)
    - Total tax (line 24)
    """
    module = "taxCalculations"

    # --- Schedule 2 additional taxes placeholder ---
    # Will be populated by build_additional_taxes_module
    graph.register_derived(
        "/schedule2AdditionalTaxes", "Schedule 2 Additional Taxes",
        FactType.DECIMAL, module,
        dependencies=["/additionalMedicareTax", "/netInvestmentIncomeTax"],
        derive_fn=lambda d: _round(
            _d(d.get("/additionalMedicareTax"))
            + _d(d.get("/netInvestmentIncomeTax"))
        ),
        export_downstream=True,
    )

    # --- Total tentative tax (Line 18) = bracket tax + Schedule 2 ---
    # Ports /totalTentativeTax
    graph.register_derived(
        "/totalTentativeTax", "Total Tentative Tax (Line 18)",
        FactType.DECIMAL, module,
        dependencies=["/tentativeTaxFromTaxableIncome", "/schedule2AdditionalTaxes"],
        derive_fn=lambda d: _round(
            _d(d.get("/tentativeTaxFromTaxableIncome"))
            + _d(d.get("/schedule2AdditionalTaxes"))
        ),
        export_mef=True, export_downstream=True,
    )

    # --- Non-refundable credits (simplified; Line 21) ---
    graph.register_writable(
        "/childTaxCredit", "Child Tax Credit", FactType.DECIMAL, module,
        description="Child Tax Credit and Other Dependent Credit (Schedule 8812)",
    )
    graph.register_writable(
        "/otherNonRefundableCredits", "Other Non-Refundable Credits",
        FactType.DECIMAL, module,
        description="Other non-refundable credits (CDCC, saver's, elderly/disabled, etc.)",
    )

    graph.register_derived(
        "/nonRefundableCredits", "Non-Refundable Credits (Line 21)",
        FactType.DECIMAL, module,
        dependencies=["/childTaxCredit", "/otherNonRefundableCredits"],
        derive_fn=lambda d: _round(sum(_d(v) for v in d.values())),
        export_mef=True,
    )

    # --- Tax less non-refundable credits (Line 22) ---
    # Ports /taxLessNonRefundableCredits = max(tentative - credits, 0)
    graph.register_derived(
        "/taxLessNonRefundableCredits", "Tax Less Non-Refundable Credits (Line 22)",
        FactType.DECIMAL, module,
        dependencies=["/totalTentativeTax", "/nonRefundableCredits"],
        derive_fn=lambda d: _round(max(
            _d(d.get("/totalTentativeTax")) - _d(d.get("/nonRefundableCredits")),
            Decimal("0"),
        )),
        export_mef=True,
    )

    # --- Total tax (Line 24) ---
    # Ports /totalTax = taxLessNonRefundableCredits (+ other taxes not yet modeled)
    graph.register_derived(
        "/totalTax", "Total Tax (Line 24)", FactType.DECIMAL, module,
        dependencies=["/taxLessNonRefundableCredits"],
        derive_fn=lambda d: _round(_d(d.get("/taxLessNonRefundableCredits"))),
        export_mef=True, export_downstream=True,
    )


# ============================================================
# Module: Additional Taxes (Medicare surtax, NIIT)
# ============================================================

def build_additional_taxes_module(graph: FactGraph):
    """
    Register Additional Medicare Tax and Net Investment Income Tax.

    Additional Medicare Tax (Form 8959): 0.9% on wages exceeding threshold.
    NIIT (Form 8960): 3.8% on lesser of net investment income or
    MAGI excess over threshold.

    Thresholds vary by filing status.
    """
    module = "additionalTaxes"

    # --- Additional Medicare Tax (0.9%) ---
    # Threshold depends on filing status
    graph.register_derived(
        "/additionalMedicareTaxThreshold", "Medicare Surtax Threshold",
        FactType.DECIMAL, module,
        dependencies=["/isFilingStatusMFJ", "/isFilingStatusMFS"],
        derive_fn=lambda d: (
            MEDICARE_TAX_THRESHOLD_MFJ if d.get("/isFilingStatusMFJ")
            else MEDICARE_TAX_THRESHOLD_MFS if d.get("/isFilingStatusMFS")
            else MEDICARE_TAX_THRESHOLD_SINGLE_HOH_QSS
        ),
    )

    # Medicare wages subject to additional tax
    graph.register_derived(
        "/additionalMedicareTaxableWages", "Wages Subject to Additional Medicare Tax",
        FactType.DECIMAL, module,
        dependencies=["/totalW2MedicareWages", "/additionalMedicareTaxThreshold"],
        derive_fn=lambda d: max(
            _d(d.get("/totalW2MedicareWages")) - _d(d.get("/additionalMedicareTaxThreshold")),
            Decimal("0"),
        ),
    )

    # Additional Medicare Tax amount
    graph.register_derived(
        "/additionalMedicareTax", "Additional Medicare Tax (Form 8959)",
        FactType.DECIMAL, module,
        dependencies=["/additionalMedicareTaxableWages"],
        derive_fn=lambda d: _round(
            _d(d.get("/additionalMedicareTaxableWages")) * ADDITIONAL_MEDICARE_TAX_RATE
        ),
        export_mef=True, export_downstream=True,
    )

    # --- Net Investment Income Tax (3.8%) ---
    # NIIT threshold depends on filing status
    graph.register_derived(
        "/niitThreshold", "NIIT MAGI Threshold", FactType.DECIMAL, module,
        dependencies=["/isFilingStatusMFJ", "/isFilingStatusQSS", "/isFilingStatusMFS"],
        derive_fn=lambda d: (
            NIIT_THRESHOLD_MFJ_QSS
            if d.get("/isFilingStatusMFJ") or d.get("/isFilingStatusQSS")
            else NIIT_THRESHOLD_MFS if d.get("/isFilingStatusMFS")
            else NIIT_THRESHOLD_SINGLE_HOH
        ),
    )

    # Net investment income (simplified: interest + dividends + capital gains)
    # In full implementation, includes rental income, royalties, etc.
    graph.register_derived(
        "/netInvestmentIncome", "Net Investment Income", FactType.DECIMAL, module,
        dependencies=["/interestIncome", "/ordinaryDividends", "/capitalGainsOrLosses"],
        derive_fn=lambda d: max(
            _d(d.get("/interestIncome"))
            + _d(d.get("/ordinaryDividends"))
            + _d(d.get("/capitalGainsOrLosses")),
            Decimal("0"),
        ),
    )

    # MAGI excess over threshold
    graph.register_derived(
        "/niitMagiExcess", "MAGI Excess Over NIIT Threshold", FactType.DECIMAL, module,
        dependencies=["/agi", "/niitThreshold"],
        derive_fn=lambda d: max(
            _d(d.get("/agi")) - _d(d.get("/niitThreshold")),
            Decimal("0"),
        ),
    )

    # NIIT = 3.8% × min(net investment income, MAGI excess)
    graph.register_derived(
        "/netInvestmentIncomeTax", "Net Investment Income Tax (Form 8960)",
        FactType.DECIMAL, module,
        dependencies=["/netInvestmentIncome", "/niitMagiExcess"],
        derive_fn=lambda d: _round(
            NIIT_RATE * min(
                _d(d.get("/netInvestmentIncome")),
                _d(d.get("/niitMagiExcess")),
            )
        ),
        export_mef=True, export_downstream=True,
    )


# ============================================================
# Module: Payments & Refund/Balance Due
# ============================================================

def build_payments_module(graph: FactGraph):
    """
    Register withholding, payments, and refund/balance due facts.

    Ports the bottom section of taxCalculations.xml:
    - W-2 withholding, 1099 withholding
    - Total withholding (line 25d)
    - Refundable credits (line 32, simplified)
    - Total payments (line 33)
    - Overpayment / refund (line 34)
    - Balance due (line 37)
    """
    module = "payments"

    # --- W-2 withholding (writable aggregate) ---
    graph.register_writable(
        "/formW2Withholding", "Total W-2 Federal Tax Withheld",
        FactType.DECIMAL, module,
        description="Sum of all W-2 Box 2 federal income tax withheld",
        export_mef=True,
    )

    # --- Estimated tax payments ---
    graph.register_writable(
        "/estimatedTaxPayments", "Estimated Tax Payments",
        FactType.DECIMAL, module,
        description="Estimated tax payments and amount applied from prior year",
    )

    # --- Refundable credits (simplified) ---
    graph.register_writable(
        "/earnedIncomeCredit", "Earned Income Credit", FactType.DECIMAL, module,
        description="Earned Income Tax Credit (EITC)",
    )
    graph.register_writable(
        "/additionalChildTaxCredit", "Additional Child Tax Credit",
        FactType.DECIMAL, module,
        description="Additional (refundable) child tax credit from Schedule 8812",
    )
    graph.register_writable(
        "/premiumTaxCreditRefund", "Net Premium Tax Credit",
        FactType.DECIMAL, module,
        description="Net premium tax credit (Form 8962)",
    )

    # --- Total withholding (Line 25d) ---
    # Ports /totalWithholding = W-2 withholding + 1099 withholding
    graph.register_derived(
        "/totalWithholding", "Total Withholding (Line 25d)", FactType.DECIMAL, module,
        dependencies=["/formW2Withholding", "/form1099InterestWithholding"],
        derive_fn=lambda d: _round(sum(_d(v) for v in d.values())),
        export_mef=True,
    )

    # --- Total refundable credits (Line 32) ---
    graph.register_derived(
        "/totalRefundableCredits", "Total Refundable Credits (Line 32)",
        FactType.DECIMAL, module,
        dependencies=[
            "/earnedIncomeCredit", "/additionalChildTaxCredit",
            "/premiumTaxCreditRefund",
        ],
        derive_fn=lambda d: _round(sum(_d(v) for v in d.values())),
        export_mef=True,
    )

    # --- Total payments (Line 33) ---
    # Ports /totalPayments = withholding + estimated + refundable credits
    graph.register_derived(
        "/totalPayments", "Total Payments (Line 33)", FactType.DECIMAL, module,
        dependencies=[
            "/totalWithholding", "/estimatedTaxPayments", "/totalRefundableCredits",
        ],
        derive_fn=lambda d: _round(sum(_d(v) for v in d.values())),
        export_mef=True,
    )

    # --- Overpayment / Refund (Line 34) ---
    # Ports /overpayment = max(totalPayments - totalTax, 0)
    graph.register_derived(
        "/overpayment", "Overpayment (Line 34)", FactType.DECIMAL, module,
        dependencies=["/totalPayments", "/totalTax"],
        derive_fn=lambda d: _round(max(
            _d(d.get("/totalPayments")) - _d(d.get("/totalTax")),
            Decimal("0"),
        )),
        export_mef=True,
    )

    # --- Due refund? ---
    graph.register_derived(
        "/dueRefund", "Due Refund?", FactType.BOOLEAN, module,
        dependencies=["/overpayment"],
        derive_fn=lambda d: _d(d.get("/overpayment")) > 0,
        export_downstream=True,
    )

    # --- Balance due (Line 37) ---
    # Ports /balanceDue = max(totalTax - totalPayments, 0)
    graph.register_derived(
        "/balanceDue", "Balance Due (Line 37)", FactType.DECIMAL, module,
        dependencies=["/totalTax", "/totalPayments"],
        derive_fn=lambda d: _round(max(
            _d(d.get("/totalTax")) - _d(d.get("/totalPayments")),
            Decimal("0"),
        )),
        export_mef=True,
    )

    # --- Owes balance? ---
    graph.register_derived(
        "/owesBalance", "Owes Balance?", FactType.BOOLEAN, module,
        dependencies=["/balanceDue"],
        derive_fn=lambda d: _d(d.get("/balanceDue")) > 0,
        export_downstream=True,
    )

    # --- Final tax amount (positive = owe, negative = refund) ---
    graph.register_derived(
        "/finalTaxAmount", "Final Tax Amount", FactType.DECIMAL, module,
        dependencies=["/totalTax", "/totalPayments"],
        derive_fn=lambda d: _d(d.get("/totalTax")) - _d(d.get("/totalPayments")),
    )


# ============================================================
# Convenience: Register Everything
# ============================================================

def register_all_federal_core(graph: FactGraph):
    """
    Register all federal core tax modules into a FactGraph.

    Order matters — modules with dependencies must come after their providers.
    Mirrors the module loading order from Direct File's XML configuration.
    """
    build_filing_status_module(graph)        # filing status flags
    build_standard_deduction_module(graph)   # needs filing status
    build_interest_income_module(graph)      # 1099-INT
    build_income_module(graph)               # needs interest, filing status
    build_additional_taxes_module(graph)     # needs income, filing status
    build_tax_bracket_module(graph)          # needs taxable income, filing status
    build_tax_calculation_module(graph)      # needs brackets, additional taxes
    build_payments_module(graph)             # needs total tax
