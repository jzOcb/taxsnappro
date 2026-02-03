"""
Income Sources Module — W-2, HSA (Form 8889), and Social Security Benefits.

Ported from IRS Direct File XML fact dictionaries:
  - formW2s.xml    → Enhanced W-2 module with all boxes and Box 12 codes
  - hsa.xml        → HSA contributions, distributions, deduction (Form 8889)
  - socialSecurity.xml → Taxable Social Security worksheet (1040 instructions)

Tax Year: 2025
Reference: IRS Direct File fact-dictionary/generate-src/xml-src/
"""

from decimal import Decimal
from typing import Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fact_graph import FactGraph, FactType


# ============================================================
# 2025 Tax Year Constants
# ============================================================

# Social Security wage base (OASDI cap)
# https://www.ssa.gov/oact/cola/cbb.html
SS_WAGE_CAP_2025 = Decimal("176100")

# HSA contribution limits (2025, Rev. Proc. 2024-25)
HSA_LIMIT_SELF_2025 = Decimal("4300")
HSA_LIMIT_FAMILY_2025 = Decimal("8550")
HSA_CATCHUP_55_PLUS = Decimal("1000")

# HSA excess contribution penalty rate
HSA_EXCESS_PENALTY_RATE = Decimal("0.06")

# Social Security Benefits Worksheet thresholds (IRC §86)
SS_PROVISIONAL_THRESHOLD_SINGLE = Decimal("25000")
SS_PROVISIONAL_THRESHOLD_MFJ = Decimal("32000")
SS_UPPER_THRESHOLD_SINGLE = Decimal("34000")  # 25000 + 9000
SS_UPPER_THRESHOLD_MFJ = Decimal("44000")      # 32000 + 12000
SS_BRACKET_WIDTH_SINGLE = Decimal("9000")       # §86(c)(2) - §86(c)(1) diff
SS_BRACKET_WIDTH_MFJ = Decimal("12000")

# Additional Medicare Tax thresholds
MEDICARE_THRESHOLD_MFS = Decimal("125000")
MEDICARE_THRESHOLD_MFJ = Decimal("250000")
MEDICARE_THRESHOLD_OTHER = Decimal("200000")

# W-2 Box 12 code mapping (letter → key name, matching Direct File XML)
BOX_12_CODES = {
    'A': 'uncollectedOasdiTaxOnTips',
    'B': 'uncollectedMedicareTaxOnTips',
    'C': 'taxableLifeInsuranceOver50k',
    'D': '401kDeferrals',
    'E': '403bDeferrals',
    'F': 'sarsepDeferrals',
    'G': '457bDeferrals',
    'H': '501c18Deferrals',
    'J': 'nontaxableSickPay',
    'K': 'goldenParachuteExciseTax',
    'L': 'expenseReimbursements',
    'M': 'uncollectedOasdiTaxOnLifeInsuranceOver50k',
    'N': 'uncollectedMedicareTaxOnLifeInsuranceOver50k',
    'P': 'armedForcesMovingExpenses',
    'Q': 'combatPay',
    'R': 'archerMsaContributions',
    'S': 'simpleContributions',
    'T': 'adoptionBenefits',
    'V': 'nsoIncome',
    'W': 'employerHsaContributions',
    'Y': '409aDeferrals',
    'Z': 'nqdcDeferrals',
    'AA': 'roth401kContributions',
    'BB': 'roth403bContributions',
    'DD': 'healthCoverageCost',
    'EE': 'roth457bContributions',
    'FF': 'qsehraBenefits',
    'GG': '83iIncome',
    'HH': '83iDeferrals',
    'II': 'nonTaxableMedicaidWaiverPayments',
}


# ============================================================
# Helper: safe Decimal get
# ============================================================

def _d(deps: dict, path: str, default: Decimal = Decimal("0")) -> Decimal:
    """Safely get a Decimal value from deps, defaulting to 0."""
    val = deps.get(path)
    if val is None:
        return default
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


# ============================================================
# B) Enhanced W-2 Module
# ============================================================

def build_w2_module(graph: FactGraph, w2_index: int = 0, filer: str = "primary"):
    """
    Register all W-2 box facts for a single W-2.

    Matches Direct File's formW2s.xml with Boxes 1-20, Box 12 codes,
    Box 13 checkboxes, and derived aggregation fields.

    Args:
        graph: The FactGraph to register into
        w2_index: Index of this W-2 (0, 1, 2, ...)
        filer: "primary" or "spouse"
    """
    module = "formW2s"
    prefix = f"/filers/{filer}/w2s/{w2_index}"

    # === Employer identification ===
    graph.register_writable(f"{prefix}/employerName", "Employer Name (Box c)", FactType.STRING, module)
    graph.register_writable(f"{prefix}/employerEin", "Employer EIN (Box b)", FactType.STRING, module,
                           export_mef=True,
                           validators=[lambda v: "EIN must be 9 digits" if v and len(str(v).replace("-", "")) != 9 else None])

    # === Core wage/tax boxes (1-6) ===
    graph.register_writable(f"{prefix}/wages", "Wages, tips, other compensation (Box 1)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/federalTaxWithheld", "Federal income tax withheld (Box 2)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/socialSecurityWages", "Social security wages (Box 3)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/socialSecurityTax", "Social security tax withheld (Box 4)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/medicareWages", "Medicare wages and tips (Box 5)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/medicareTax", "Medicare tax withheld (Box 6)",
                           FactType.DECIMAL, module, export_mef=True)

    # === Tips and allocated tips (7-8) ===
    graph.register_writable(f"{prefix}/socialSecurityTips", "Social security tips (Box 7)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/allocatedTips", "Allocated tips (Box 8)",
                           FactType.DECIMAL, module, export_mef=True)

    # === Box 9 is intentionally blank on current W-2 forms ===

    # === Dependent care benefits (Box 10) ===
    graph.register_writable(f"{prefix}/dependentCareBenefits", "Dependent care benefits (Box 10)",
                           FactType.DECIMAL, module, export_mef=True)

    # === Non-qualified plans (Box 11) ===
    graph.register_writable(f"{prefix}/nonQualifiedPlans", "Non-qualified plans (Box 11)",
                           FactType.DECIMAL, module, export_mef=True)

    # === Box 12 codes (a-d slots, each has a code letter and amount) ===
    # Register the most common/important Box 12 code amounts
    for code_letter, code_name in BOX_12_CODES.items():
        graph.register_writable(
            f"{prefix}/box12/{code_name}",
            f"Box 12 Code {code_letter} - {code_name}",
            FactType.DECIMAL, module, export_mef=True,
        )

    # === Box 13 checkboxes ===
    graph.register_writable(f"{prefix}/retirementPlan", "Retirement plan participant (Box 13)",
                           FactType.BOOLEAN, module, export_mef=True)
    graph.register_writable(f"{prefix}/statutoryEmployee", "Statutory employee (Box 13)",
                           FactType.BOOLEAN, module, export_mef=True)
    graph.register_writable(f"{prefix}/thirdPartySickPay", "Third-party sick pay (Box 13)",
                           FactType.BOOLEAN, module, export_mef=True)

    # === Box 14 - Other (free-form, state-specific) ===
    graph.register_writable(f"{prefix}/box14Other", "Other (Box 14)", FactType.STRING, module)

    # === State/local section (Boxes 15-20) ===
    graph.register_writable(f"{prefix}/stateCode", "State (Box 15)", FactType.STRING, module)
    graph.register_writable(f"{prefix}/stateEmployerId", "State employer ID (Box 15)",
                           FactType.STRING, module, export_mef=True)
    graph.register_writable(f"{prefix}/stateWages", "State wages (Box 16)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/stateTaxWithheld", "State income tax (Box 17)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/localWages", "Local wages (Box 18)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/localTaxWithheld", "Local income tax (Box 19)",
                           FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/localityName", "Locality name (Box 20)",
                           FactType.STRING, module)

    # === Corrected / Nonstandard indicators ===
    graph.register_writable(f"{prefix}/isCorrected", "Is corrected W-2", FactType.BOOLEAN, module)
    graph.register_writable(f"{prefix}/isNonstandard", "Is nonstandard W-2", FactType.BOOLEAN, module)

    # --- Derived: SS wages capped at statutory limit per W-2 ---
    graph.register_derived(
        f"{prefix}/ssWagesCapped", "SS Wages (capped at statutory limit)", FactType.DECIMAL, module,
        dependencies=[f"{prefix}/socialSecurityWages"],
        derive_fn=lambda deps: min(
            _d(deps, list(deps.keys())[0]) if deps else Decimal("0"),
            SS_WAGE_CAP_2025
        ),
    )

    # --- Derived: has employer HSA contributions (Box 12 code W) ---
    graph.register_derived(
        f"{prefix}/hasEmployerHsaContributions",
        "Has employer HSA contributions (Box 12 code W)",
        FactType.BOOLEAN, module,
        dependencies=[f"{prefix}/box12/employerHsaContributions"],
        derive_fn=lambda deps: any(
            v is not None and v > Decimal("0") for v in deps.values()
        ),
    )


def build_w2_aggregation_module(graph: FactGraph, filer: str = "primary", w2_count: int = 1):
    """
    Register derived facts that aggregate across all W-2s for a filer.

    Args:
        graph: The FactGraph
        filer: "primary" or "spouse"
        w2_count: Number of W-2s registered for this filer
    """
    module = "formW2s"
    prefix = f"/filers/{filer}"

    # Build dependency lists
    wage_deps = [f"{prefix}/w2s/{i}/wages" for i in range(w2_count)]
    fed_wh_deps = [f"{prefix}/w2s/{i}/federalTaxWithheld" for i in range(w2_count)]
    ss_wage_deps = [f"{prefix}/w2s/{i}/socialSecurityWages" for i in range(w2_count)]
    ss_tax_deps = [f"{prefix}/w2s/{i}/socialSecurityTax" for i in range(w2_count)]
    medicare_wage_deps = [f"{prefix}/w2s/{i}/medicareWages" for i in range(w2_count)]
    medicare_tax_deps = [f"{prefix}/w2s/{i}/medicareTax" for i in range(w2_count)]
    state_wh_deps = [f"{prefix}/w2s/{i}/stateTaxWithheld" for i in range(w2_count)]
    hsa_w_deps = [f"{prefix}/w2s/{i}/box12/employerHsaContributions" for i in range(w2_count)]
    retirement_deps = [f"{prefix}/w2s/{i}/retirementPlan" for i in range(w2_count)]

    def _sum_deps(deps: dict) -> Decimal:
        return sum((_d(deps, k) for k in deps), Decimal("0"))

    # --- Total wages for this filer ---
    graph.register_derived(
        f"{prefix}/totalWages", f"Total W-2 Wages ({filer})", FactType.DECIMAL, module,
        dependencies=wage_deps,
        derive_fn=_sum_deps,
        export_mef=True, export_downstream=True,
    )

    # --- Total federal withholding ---
    graph.register_derived(
        f"{prefix}/totalFederalWithholding", f"Total Federal Withholding ({filer})",
        FactType.DECIMAL, module,
        dependencies=fed_wh_deps,
        derive_fn=_sum_deps,
        export_mef=True, export_downstream=True,
    )

    # --- Total SS wages ---
    graph.register_derived(
        f"{prefix}/totalSsWages", f"Total SS Wages ({filer})", FactType.DECIMAL, module,
        dependencies=ss_wage_deps,
        derive_fn=_sum_deps,
        export_downstream=True,
    )

    # --- Total SS tax withheld ---
    graph.register_derived(
        f"{prefix}/totalSsTax", f"Total SS Tax ({filer})", FactType.DECIMAL, module,
        dependencies=ss_tax_deps,
        derive_fn=_sum_deps,
        export_downstream=True,
    )

    # --- Total Medicare wages ---
    graph.register_derived(
        f"{prefix}/totalMedicareWages", f"Total Medicare Wages ({filer})", FactType.DECIMAL, module,
        dependencies=medicare_wage_deps,
        derive_fn=_sum_deps,
        export_downstream=True,
    )

    # --- Total Medicare tax ---
    graph.register_derived(
        f"{prefix}/totalMedicareTax", f"Total Medicare Tax ({filer})", FactType.DECIMAL, module,
        dependencies=medicare_tax_deps,
        derive_fn=_sum_deps,
        export_downstream=True,
    )

    # --- Total state withholding ---
    graph.register_derived(
        f"{prefix}/totalStateWithholding", f"Total State Withholding ({filer})",
        FactType.DECIMAL, module,
        dependencies=state_wh_deps,
        derive_fn=_sum_deps,
        export_downstream=True,
    )

    # --- Total employer HSA contributions (Box 12 code W) ---
    graph.register_derived(
        f"{prefix}/totalEmployerHsaContributions",
        f"Total Employer HSA Contributions ({filer})",
        FactType.DECIMAL, module,
        dependencies=hsa_w_deps,
        derive_fn=_sum_deps,
        export_downstream=True,
    )

    # --- SS wage cap exceeded (multiple W-2s from different employers) ---
    graph.register_derived(
        f"{prefix}/exceedsSsWageCap",
        f"SS wages exceed cap ({filer})",
        FactType.BOOLEAN, module,
        dependencies=[f"{prefix}/totalSsWages"],
        derive_fn=lambda deps: _d(deps, f"{prefix}/totalSsWages") > SS_WAGE_CAP_2025,
        description=f"Whether {filer}'s total SS wages exceed ${SS_WAGE_CAP_2025} (2025 cap). "
                    "May be entitled to refund of excess SS tax if multiple employers.",
    )

    # --- Excess SS tax paid (potential refund) ---
    # Maximum SS tax per person = 6.2% × wage cap
    max_ss_tax = SS_WAGE_CAP_2025 * Decimal("0.062")
    graph.register_derived(
        f"{prefix}/excessSsTaxPaid",
        f"Excess SS Tax Paid ({filer})",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/totalSsTax"],
        derive_fn=lambda deps: max(
            _d(deps, f"{prefix}/totalSsTax") - max_ss_tax,
            Decimal("0")
        ),
        description="Refundable credit for excess Social Security tax withheld from multiple employers.",
    )

    # --- Any retirement plan indicator ---
    graph.register_derived(
        f"{prefix}/hasRetirementPlan",
        f"Has retirement plan on any W-2 ({filer})",
        FactType.BOOLEAN, module,
        dependencies=retirement_deps,
        derive_fn=lambda deps: any(v is True for v in deps.values()),
        description="Whether any W-2 has the retirement plan box checked. "
                    "Affects IRA deduction eligibility.",
    )

    # --- Has employer HSA contributions from any W-2 ---
    graph.register_derived(
        f"{prefix}/hasHsaContributionsFromW2s",
        f"Has HSA contributions on W-2s ({filer})",
        FactType.BOOLEAN, module,
        dependencies=hsa_w_deps,
        derive_fn=lambda deps: any(
            v is not None and v > Decimal("0") for v in deps.values()
        ),
        export_downstream=True,
    )


def build_all_w2_aggregation(graph: FactGraph,
                              primary_w2_count: int = 1,
                              spouse_w2_count: int = 0):
    """
    Register return-level W-2 aggregation facts across all filers.
    """
    module = "formW2s"

    # Build dependency lists for both filers
    deps_wages = [f"/filers/primary/totalWages"]
    deps_fed_wh = [f"/filers/primary/totalFederalWithholding"]
    deps_medicare = [f"/filers/primary/totalMedicareWages"]

    if spouse_w2_count > 0:
        deps_wages.append("/filers/spouse/totalWages")
        deps_fed_wh.append("/filers/spouse/totalFederalWithholding")
        deps_medicare.append("/filers/spouse/totalMedicareWages")

    def _sum_deps(deps: dict) -> Decimal:
        return sum((_d(deps, k) for k in deps), Decimal("0"))

    # --- Return-level total wages (all filers, all W-2s) ---
    graph.register_derived(
        "/totalW2Wages", "Total W-2 Wages (all filers)", FactType.DECIMAL, module,
        dependencies=deps_wages,
        derive_fn=_sum_deps,
        export_mef=True, export_downstream=True,
    )

    # --- Return-level total federal withholding ---
    graph.register_derived(
        "/totalW2FederalWithholding", "Total Federal Withholding (all W-2s)",
        FactType.DECIMAL, module,
        dependencies=deps_fed_wh,
        derive_fn=_sum_deps,
        export_mef=True, export_downstream=True,
    )

    # --- Return-level total Medicare wages ---
    graph.register_derived(
        "/totalMedicareWages", "Total Medicare Wages (all filers)", FactType.DECIMAL, module,
        dependencies=deps_medicare,
        derive_fn=_sum_deps,
        export_downstream=True,
    )

    # --- Additional Medicare Tax threshold (filing-status dependent) ---
    graph.register_derived(
        "/medicareAdditionalTaxThreshold",
        "Additional Medicare Tax threshold",
        FactType.DECIMAL, module,
        dependencies=["/filingStatus"],
        derive_fn=lambda deps: (
            MEDICARE_THRESHOLD_MFJ if deps.get("/filingStatus") == "married_filing_jointly"
            else MEDICARE_THRESHOLD_MFS if deps.get("/filingStatus") == "married_filing_separately"
            else MEDICARE_THRESHOLD_OTHER
        ),
        description="Filing-status threshold for Additional Medicare Tax (Form 8959).",
    )


# ============================================================
# A) HSA Module (Form 8889)
# ============================================================

def build_hsa_module(graph: FactGraph, filer: str = "primary"):
    """
    Register HSA (Form 8889) facts for a single filer.

    Implements:
      - Part I: HSA contributions and deduction
      - Part II: HSA distributions (simplified)
      - Excess contribution penalty
      - 2025 contribution limits with catch-up

    Args:
        graph: The FactGraph
        filer: "primary" or "spouse"
    """
    module = "hsa"
    prefix = f"/filers/{filer}/hsa"
    w2_hsa_path = f"/filers/{filer}/totalEmployerHsaContributions"

    # =============================================
    # Writable facts (user-entered)
    # =============================================

    # --- Coverage type ---
    graph.register_writable(
        f"{prefix}/coverageType", "HDHP coverage type (self-only or family)",
        FactType.ENUM, module,
        description="Whether the filer had self-only or family HDHP coverage. "
                    "Determines contribution limit.",
    )

    # --- Coverage duration ---
    graph.register_writable(
        f"{prefix}/coveredAllYear", "Covered by HDHP all year",
        FactType.BOOLEAN, module,
        description="Whether the filer was covered by a qualifying HDHP for the entire tax year.",
    )

    graph.register_writable(
        f"{prefix}/monthsCovered", "Months covered by HDHP",
        FactType.INTEGER, module,
        description="Number of months covered if not covered all year (1-12).",
        validators=[lambda v: "Must be 1-12" if v is not None and (v < 1 or v > 12) else None],
    )

    # --- Age indicator ---
    graph.register_writable(
        f"{prefix}/is55OrOlder", "Age 55 or older by end of tax year",
        FactType.BOOLEAN, module,
        description="Whether the filer was 55+ by Dec 31, 2025. Eligible for $1,000 catch-up.",
    )

    # --- Personal (non-employer) contributions ---
    graph.register_writable(
        f"{prefix}/personalContributions",
        "Personal HSA contributions (not through employer)",
        FactType.DECIMAL, module,
        description="Additional HSA contributions made directly by the taxpayer "
                    "(not from W-2 Box 12 code W).",
        validators=[lambda v: "Cannot be negative" if v is not None and v < 0 else None],
    )

    # --- Contributions made between Jan 1 and Apr 15 of next year for this TY ---
    graph.register_writable(
        f"{prefix}/contributionsMadeNextYear",
        "HSA contributions made Jan-Apr 2026 for TY 2025",
        FactType.DECIMAL, module,
        description="HSA contributions made between Jan 1 and Apr 15, 2026 "
                    "designated for tax year 2025.",
    )

    # --- Distributions (from Form 1099-SA) ---
    graph.register_writable(
        f"{prefix}/totalDistributions", "Total HSA distributions (1099-SA Box 1)",
        FactType.DECIMAL, module, export_mef=True,
        description="Gross distributions from all HSA accounts (Form 1099-SA, Box 1).",
    )

    graph.register_writable(
        f"{prefix}/distributionsForMedical",
        "Distributions used for qualified medical expenses",
        FactType.DECIMAL, module,
        description="Amount of HSA distributions used for qualified medical expenses. "
                    "Form 8889 line 15.",
    )

    graph.register_writable(
        f"{prefix}/distributionsRolledOver", "HSA distributions rolled over to another HSA",
        FactType.DECIMAL, module,
        description="Amount of distributions rolled over to another HSA within 60 days.",
    )

    # --- Prior year excess contributions ---
    graph.register_writable(
        f"{prefix}/priorYearExcessContributions",
        "Excess contributions from prior year",
        FactType.DECIMAL, module,
        description="Excess HSA contributions carried forward from the prior tax year.",
    )

    # --- Enrolled in Medicare ---
    graph.register_writable(
        f"{prefix}/enrolledInMedicare", "Enrolled in Medicare",
        FactType.ENUM, module,
        description="Whether the filer was enrolled in Medicare (allYear/partOfYear/noneOfYear).",
    )

    # --- Qualified HSA funding distribution ---
    graph.register_writable(
        f"{prefix}/qualifiedFundingDistribution",
        "Qualified HSA funding distribution",
        FactType.DECIMAL, module,
        description="One-time transfer from IRA to HSA (Form 8889 line 10). Typically $0.",
    )

    # =============================================
    # Derived facts (calculated)
    # =============================================

    # --- Annual contribution limit (before catch-up, before proration) ---
    graph.register_derived(
        f"{prefix}/annualLimit", "Annual HSA contribution limit",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/coverageType"],
        derive_fn=lambda deps: (
            HSA_LIMIT_FAMILY_2025 if deps.get(f"{prefix}/coverageType") == "family"
            else HSA_LIMIT_SELF_2025
        ),
        description="Base annual HSA limit: $4,300 self-only, $8,550 family (2025).",
    )

    # --- Prorated limit (for partial year coverage) ---
    graph.register_derived(
        f"{prefix}/proratedLimit", "Prorated HSA limit",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/annualLimit", f"{prefix}/coveredAllYear", f"{prefix}/monthsCovered"],
        derive_fn=lambda deps: (
            _d(deps, f"{prefix}/annualLimit")
            if deps.get(f"{prefix}/coveredAllYear") is True
            else (
                (_d(deps, f"{prefix}/annualLimit") * Decimal(str(deps.get(f"{prefix}/monthsCovered", 12) or 12)))
                / Decimal("12")
            ).quantize(Decimal("1"))
        ),
        description="HSA limit prorated for partial-year HDHP coverage (Form 8889, line 3).",
    )

    # --- Contribution limit with catch-up ---
    graph.register_derived(
        f"{prefix}/contributionLimit", "HSA contribution limit (with catch-up)",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/proratedLimit", f"{prefix}/is55OrOlder"],
        derive_fn=lambda deps: (
            _d(deps, f"{prefix}/proratedLimit")
            + (HSA_CATCHUP_55_PLUS if deps.get(f"{prefix}/is55OrOlder") else Decimal("0"))
        ),
        description="Total HSA contribution limit including $1,000 catch-up if 55+. "
                    "Form 8889 line 7.",
        export_mef=True,
    )

    # --- Total contributions (employer + personal) ---
    # Form 8889 Line 2 = employer (W-2 code W) + personal
    graph.register_derived(
        f"{prefix}/totalContributions", "Total HSA contributions",
        FactType.DECIMAL, module,
        dependencies=[w2_hsa_path, f"{prefix}/personalContributions"],
        derive_fn=lambda deps: (
            _d(deps, w2_hsa_path)
            + _d(deps, f"{prefix}/personalContributions")
        ),
        description="Total contributions: employer (W-2 Box 12 code W) + personal. "
                    "Form 8889 line 2.",
        export_mef=True,
    )

    # --- HSA deduction (Line 13 of Form 8889) ---
    # Deduction = lesser of (total contributions - employer portion) and (limit - employer portion)
    # But employer contributions count toward the limit
    graph.register_derived(
        f"{prefix}/deduction", "HSA deduction (Form 8889 line 13)",
        FactType.DECIMAL, module,
        dependencies=[
            f"{prefix}/totalContributions",
            w2_hsa_path,
            f"{prefix}/contributionLimit",
            f"{prefix}/qualifiedFundingDistribution",
        ],
        derive_fn=lambda deps: _compute_hsa_deduction(deps, prefix, w2_hsa_path),
        description="HSA deduction = personal contributions limited by remaining room after "
                    "employer contributions. Reported on Schedule 1, line 13.",
        export_mef=True, export_downstream=True,
    )

    # --- Excess contributions ---
    graph.register_derived(
        f"{prefix}/excessContributions", "Excess HSA contributions",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/totalContributions", f"{prefix}/contributionLimit"],
        derive_fn=lambda deps: max(
            _d(deps, f"{prefix}/totalContributions") - _d(deps, f"{prefix}/contributionLimit"),
            Decimal("0"),
        ),
        description="Contributions exceeding the annual limit. Subject to 6% excise tax.",
    )

    # --- Excess contribution penalty (6% excise tax, Form 5329 Part VII) ---
    graph.register_derived(
        f"{prefix}/excessContributionPenalty", "Excess contribution penalty (6%)",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/excessContributions", f"{prefix}/priorYearExcessContributions"],
        derive_fn=lambda deps: (
            (
                _d(deps, f"{prefix}/excessContributions")
                + _d(deps, f"{prefix}/priorYearExcessContributions")
            ) * HSA_EXCESS_PENALTY_RATE
        ).quantize(Decimal("1.00")),
        description="6% excise tax on excess HSA contributions (current + prior year carryover). "
                    "Reported on Form 5329.",
    )

    # --- Taxable HSA distributions (Form 8889 Part II, line 16) ---
    graph.register_derived(
        f"{prefix}/taxableDistributions",
        "Taxable HSA distributions",
        FactType.DECIMAL, module,
        dependencies=[
            f"{prefix}/totalDistributions",
            f"{prefix}/distributionsForMedical",
            f"{prefix}/distributionsRolledOver",
        ],
        derive_fn=lambda deps: max(
            _d(deps, f"{prefix}/totalDistributions")
            - _d(deps, f"{prefix}/distributionsForMedical")
            - _d(deps, f"{prefix}/distributionsRolledOver"),
            Decimal("0"),
        ),
        description="Distributions not used for qualified medical expenses and not rolled over. "
                    "Included in other income (Form 8889 line 16).",
        export_mef=True, export_downstream=True,
    )

    # --- Additional tax on non-qualified distributions (20%) ---
    graph.register_derived(
        f"{prefix}/additionalTaxOnDistributions",
        "Additional 20% tax on taxable HSA distributions",
        FactType.DECIMAL, module,
        dependencies=[f"{prefix}/taxableDistributions"],
        derive_fn=lambda deps: (
            _d(deps, f"{prefix}/taxableDistributions") * Decimal("0.20")
        ).quantize(Decimal("1.00")),
        description="20% additional tax on HSA distributions not used for qualified medical expenses. "
                    "Form 8889 line 17b. Exceptions for disability, death, age 65+.",
        export_mef=True,
    )


def _compute_hsa_deduction(deps: dict, prefix: str, w2_hsa_path: str) -> Decimal:
    """
    Compute HSA deduction per Form 8889, Part I.

    Deduction = min(total_contributions, contribution_limit)
                - employer_contributions (already excluded from income)
                - qualified_funding_distribution

    The deduction is the amount the taxpayer can deduct on Schedule 1, line 13.
    Employer contributions (W-2 code W) are already excluded from Box 1 wages,
    so only the personal portion is deductible.
    """
    total = _d(deps, f"{prefix}/totalContributions")
    employer = _d(deps, w2_hsa_path)
    limit = _d(deps, f"{prefix}/contributionLimit")
    qfd = _d(deps, f"{prefix}/qualifiedFundingDistribution")

    # Line 9: lesser of total contributions and limit
    line9 = min(total, limit)

    # Line 13: deduction = line 9 - employer contributions - QFD
    deduction = line9 - employer - qfd

    return max(deduction, Decimal("0"))


# ============================================================
# C) Social Security Benefits Module
# ============================================================

def build_social_security_module(graph: FactGraph):
    """
    Register Social Security benefits facts and the taxable benefits worksheet.

    Implements the Social Security Benefits Worksheet from 1040 instructions,
    which determines how much (0%, up to 50%, or up to 85%) of SS benefits
    are taxable based on provisional income.

    Reference: socialSecurity.xml, 1040 Instructions Social Security Benefits Worksheet
    """
    module = "socialSecurity"

    # =============================================
    # Writable facts
    # =============================================

    # --- Total net benefits from all SSA-1099 / RRB-1099 forms ---
    graph.register_writable(
        "/socialSecurity/totalNetBenefits",
        "Total Social Security net benefits (Box 5 of SSA-1099)",
        FactType.DECIMAL, module, export_mef=True,
        description="Net social security benefits from all SSA-1099 and RRB-1099 forms. "
                    "1040 line 6a.",
    )

    # --- Federal tax withheld from SS benefits ---
    graph.register_writable(
        "/socialSecurity/federalTaxWithheld",
        "Federal tax withheld from SS benefits",
        FactType.DECIMAL, module, export_mef=True,
        description="Federal income tax withheld from social security benefits "
                    "(SSA-1099 Box 6 / RRB-1099 Box 10).",
    )

    # --- Lived apart from spouse all year (for MFS filers) ---
    # This fact may already exist elsewhere; register only if needed
    graph.register_writable(
        "/socialSecurity/mfsLivedApartAllYear",
        "MFS: Lived apart from spouse all year",
        FactType.BOOLEAN, module,
        description="If MFS, whether filer lived apart from spouse for the entire year. "
                    "Affects SS benefits taxation threshold (code 'D').",
    )

    # =============================================
    # Derived facts — Social Security Benefits Worksheet
    # =============================================

    # --- Half of benefits (Worksheet line 1) ---
    graph.register_derived(
        "/socialSecurity/halfBenefits", "Half of Social Security benefits",
        FactType.DECIMAL, module,
        dependencies=["/socialSecurity/totalNetBenefits"],
        derive_fn=lambda deps: max(
            _d(deps, "/socialSecurity/totalNetBenefits") * Decimal("0.5"),
            Decimal("0"),
        ),
        description="50% of net social security benefits. Worksheet line 1.",
    )

    # --- Provisional income (Worksheet line 7) ---
    # Line 7 = (half benefits + other income + tax-exempt interest) - above-the-line deductions
    # We depend on AGI-related paths. The actual formula:
    #   line 3 = wages + interest + dividends + IRA + pensions + cap gains + other income
    #   line 5 = half benefits + line 3 + tax-exempt interest
    #   line 6 = adjustments to income (Sch 1, lines 11-20, 23, 25)
    #   line 7 = max(line 5 - line 6, 0)
    graph.register_derived(
        "/socialSecurity/provisionalIncome",
        "Provisional income (Worksheet line 7)",
        FactType.DECIMAL, module,
        dependencies=[
            "/socialSecurity/halfBenefits",
            "/totalW2Wages",               # 1040 line 1z (wages)
            "/totalInterestIncome",         # 1040 line 2b (taxable interest)
            "/taxExemptInterest",           # 1040 line 2a
            "/totalOrdinaryDividends",      # 1040 line 3b
        ],
        derive_fn=lambda deps: max(
            _d(deps, "/socialSecurity/halfBenefits")
            + _d(deps, "/totalW2Wages")
            + _d(deps, "/totalInterestIncome")
            + _d(deps, "/taxExemptInterest")
            + _d(deps, "/totalOrdinaryDividends"),
            Decimal("0"),
        ),
        description="Provisional income for SS benefits taxation. Simplified calculation "
                    "using available income sources. Worksheet line 7.",
    )

    # --- Filing-status threshold (Worksheet line 8) — §86(c)(1) base amount ---
    graph.register_derived(
        "/socialSecurity/baseThreshold",
        "SS benefits base threshold (Worksheet line 8)",
        FactType.DECIMAL, module,
        dependencies=["/filingStatus", "/socialSecurity/mfsLivedApartAllYear"],
        derive_fn=lambda deps: _ss_base_threshold(deps),
        description="$32,000 for MFJ, $25,000 for most others, $0 for MFS living with spouse.",
    )

    # --- Bracket width (Worksheet line 10) — difference between upper and lower thresholds ---
    graph.register_derived(
        "/socialSecurity/bracketWidth",
        "SS benefits bracket width (Worksheet line 10)",
        FactType.DECIMAL, module,
        dependencies=["/filingStatus"],
        derive_fn=lambda deps: (
            SS_BRACKET_WIDTH_MFJ if deps.get("/filingStatus") == "married_filing_jointly"
            else SS_BRACKET_WIDTH_SINGLE
        ),
        description="$12,000 for MFJ, $9,000 for others. §86(c)(2) - §86(c)(1).",
    )

    # --- Worksheet line 9: provisional income - base threshold ---
    graph.register_derived(
        "/socialSecurity/wkshtLine9",
        "Worksheet line 9",
        FactType.DECIMAL, module,
        dependencies=["/socialSecurity/provisionalIncome", "/socialSecurity/baseThreshold"],
        derive_fn=lambda deps: (
            _d(deps, "/socialSecurity/provisionalIncome")
            - _d(deps, "/socialSecurity/baseThreshold")
        ),
    )

    # --- Worksheet line 11: max(line 9 - line 10, 0) ---
    graph.register_derived(
        "/socialSecurity/wkshtLine11",
        "Worksheet line 11",
        FactType.DECIMAL, module,
        dependencies=["/socialSecurity/wkshtLine9", "/socialSecurity/bracketWidth"],
        derive_fn=lambda deps: max(
            _d(deps, "/socialSecurity/wkshtLine9")
            - _d(deps, "/socialSecurity/bracketWidth"),
            Decimal("0"),
        ),
    )

    # --- Worksheet line 16 (intermediate calculation) ---
    graph.register_derived(
        "/socialSecurity/wkshtLine16",
        "Worksheet line 16",
        FactType.DECIMAL, module,
        dependencies=[
            "/socialSecurity/totalNetBenefits",
            "/socialSecurity/wkshtLine9",
            "/socialSecurity/wkshtLine11",
            "/socialSecurity/bracketWidth",
            "/socialSecurity/provisionalIncome",
            "/socialSecurity/baseThreshold",
            "/filingStatus",
            "/socialSecurity/mfsLivedApartAllYear",
        ],
        derive_fn=lambda deps: _ss_worksheet_line16(deps),
        description="Intermediate taxable SS calculation (Worksheet line 16).",
    )

    # --- Taxable Social Security Benefits (1040 line 6b, Worksheet line 18) ---
    graph.register_derived(
        "/socialSecurity/taxableBenefits",
        "Taxable Social Security benefits (1040 line 6b)",
        FactType.DECIMAL, module,
        dependencies=[
            "/socialSecurity/totalNetBenefits",
            "/socialSecurity/wkshtLine16",
        ],
        derive_fn=lambda deps: _compute_taxable_ss(deps),
        description="Taxable portion of Social Security benefits. "
                    "Min of (worksheet line 16) and (85% × benefits). "
                    "1040 line 6b.",
        export_mef=True, export_downstream=True,
    )

    # --- Non-taxable SS benefits ---
    graph.register_derived(
        "/socialSecurity/nonTaxableBenefits",
        "Non-taxable Social Security benefits",
        FactType.DECIMAL, module,
        dependencies=["/socialSecurity/totalNetBenefits", "/socialSecurity/taxableBenefits"],
        derive_fn=lambda deps: max(
            _d(deps, "/socialSecurity/totalNetBenefits")
            - _d(deps, "/socialSecurity/taxableBenefits"),
            Decimal("0"),
        ),
        description="Used for Schedule R line 13a and other calculations.",
        export_downstream=True,
    )


def _ss_base_threshold(deps: dict) -> Decimal:
    """
    Determine the base amount threshold per §86(c)(1).
    - MFJ: $32,000
    - MFS who lived with spouse: $0 (all benefits potentially taxable)
    - MFS who lived apart all year: $25,000 (treated like single)
    - All others (single, HOH, QSS): $25,000
    """
    status = deps.get("/filingStatus")

    if status == "married_filing_jointly":
        return SS_PROVISIONAL_THRESHOLD_MFJ

    if status == "married_filing_separately":
        lived_apart = deps.get("/socialSecurity/mfsLivedApartAllYear")
        if lived_apart:
            return SS_PROVISIONAL_THRESHOLD_SINGLE
        else:
            return Decimal("0")  # MFS living together: no threshold

    return SS_PROVISIONAL_THRESHOLD_SINGLE


def _ss_worksheet_line16(deps: dict) -> Decimal:
    """
    Compute Social Security Benefits Worksheet Line 16.

    Three paths:
    1. MFS living with spouse: line 7 × 0.85 (worst case, no threshold)
    2. Provisional income < base threshold: $0 (no benefits taxable)
    3. Normal calculation: 0.85 × line 11 + min(50% × benefits, 50% × line 12)
       where line 12 = min(line 9, bracket_width)
    """
    status = deps.get("/filingStatus")
    provisional = _d(deps, "/socialSecurity/provisionalIncome")
    base_threshold = _d(deps, "/socialSecurity/baseThreshold")
    benefits = _d(deps, "/socialSecurity/totalNetBenefits")
    line9 = _d(deps, "/socialSecurity/wkshtLine9")
    line11 = _d(deps, "/socialSecurity/wkshtLine11")
    bracket = _d(deps, "/socialSecurity/bracketWidth")

    # Case 1: MFS who lived with spouse — 85% of line 7
    if status == "married_filing_separately":
        lived_apart = deps.get("/socialSecurity/mfsLivedApartAllYear")
        if not lived_apart:
            return provisional * Decimal("0.85")

    # Case 2: Provisional income below threshold — nothing taxable
    if provisional < base_threshold:
        return Decimal("0")

    # Case 3: Normal worksheet calculation
    # line 12 = min(line 9, bracket_width)
    line12 = min(line9, bracket)
    # line 13 = line 12 × 0.50
    line13 = line12 * Decimal("0.50")
    # line 14 = min(50% of benefits, line 13)
    line14 = min(benefits * Decimal("0.50"), line13)
    # line 15 = 0.85 × line 11
    line15 = line11 * Decimal("0.85")
    # line 16 = line 14 + line 15
    return line14 + line15


def _compute_taxable_ss(deps: dict) -> Decimal:
    """
    Compute taxable Social Security benefits (Worksheet line 18 / 1040 line 6b).

    = min(worksheet_line_16, 85% × total_benefits)

    If benefits are negative (repayment), taxable = $0.
    """
    benefits = _d(deps, "/socialSecurity/totalNetBenefits")

    if benefits <= Decimal("0"):
        return Decimal("0")

    line16 = _d(deps, "/socialSecurity/wkshtLine16")
    line17 = benefits * Decimal("0.85")

    return min(line16, line17).quantize(Decimal("1"))


# ============================================================
# Convenience: Build All Income Source Modules
# ============================================================

def build_income_sources(graph: FactGraph,
                          primary_w2_count: int = 1,
                          spouse_w2_count: int = 0,
                          has_hsa_primary: bool = False,
                          has_hsa_spouse: bool = False,
                          has_social_security: bool = False):
    """
    Build all income source modules and register them into the graph.

    This is the main entry point for adding W-2, HSA, and Social Security
    facts to a FactGraph.

    Args:
        graph: The FactGraph instance
        primary_w2_count: Number of W-2s for the primary filer
        spouse_w2_count: Number of W-2s for the spouse (0 if not MFJ)
        has_hsa_primary: Whether primary filer has HSA activity
        has_hsa_spouse: Whether spouse has HSA activity
        has_social_security: Whether any filer received SS benefits
    """
    # --- Register individual W-2s ---
    for i in range(primary_w2_count):
        build_w2_module(graph, w2_index=i, filer="primary")

    for i in range(spouse_w2_count):
        build_w2_module(graph, w2_index=i, filer="spouse")

    # --- Register per-filer W-2 aggregation ---
    if primary_w2_count > 0:
        build_w2_aggregation_module(graph, filer="primary", w2_count=primary_w2_count)

    if spouse_w2_count > 0:
        build_w2_aggregation_module(graph, filer="spouse", w2_count=spouse_w2_count)

    # --- Register return-level W-2 aggregation ---
    build_all_w2_aggregation(graph,
                              primary_w2_count=primary_w2_count,
                              spouse_w2_count=spouse_w2_count)

    # --- HSA modules ---
    if has_hsa_primary:
        build_hsa_module(graph, filer="primary")

    if has_hsa_spouse:
        build_hsa_module(graph, filer="spouse")

    # --- Social Security ---
    if has_social_security:
        # Ensure required upstream facts exist (may already be registered)
        _ensure_ss_upstream_facts(graph)
        build_social_security_module(graph)


def _ensure_ss_upstream_facts(graph: FactGraph):
    """
    Ensure upstream facts needed by the SS worksheet exist in the graph.
    Only registers them if they don't already exist.
    """
    # Tax-exempt interest (1040 line 2a) — needed for provisional income
    if graph.get_fact("/taxExemptInterest") is None:
        graph.register_writable(
            "/taxExemptInterest", "Tax-exempt interest (1040 line 2a)",
            FactType.DECIMAL, "interest", export_mef=True,
        )

    # Total interest income (1040 line 2b)
    if graph.get_fact("/totalInterestIncome") is None:
        graph.register_writable(
            "/totalInterestIncome", "Total taxable interest income (1040 line 2b)",
            FactType.DECIMAL, "interest", export_mef=True,
        )

    # Total ordinary dividends (1040 line 3b)
    if graph.get_fact("/totalOrdinaryDividends") is None:
        graph.register_writable(
            "/totalOrdinaryDividends", "Total ordinary dividends (1040 line 3b)",
            FactType.DECIMAL, "income", export_mef=True,
        )
