"""
Tax Year Constants — 2024 and 2025.

2024: Rev. Proc. 2023-34 (pre-OBBBA)
2025: Rev. Proc. 2024-40 + OBBBA adjustments (signed July 2025)

Use get_constants(year) to get the right set for any calculation.
"""

from decimal import Decimal
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaxYearConstants:
    """All tax constants for a given tax year."""
    year: int
    
    # Standard Deductions
    std_deduction_single: Decimal
    std_deduction_mfj: Decimal
    std_deduction_mfs: Decimal
    std_deduction_hoh: Decimal
    std_deduction_qss: Decimal
    additional_std_single_hoh: Decimal  # per qualifying item (65+/blind)
    additional_std_mfj_mfs: Decimal
    dependent_std_floor: Decimal
    dependent_earned_adder: Decimal
    
    # Federal Tax Brackets — MFJ
    brackets_mfj: tuple  # tuple of (upper, rate, base_tax, bracket_start)
    brackets_single: tuple
    brackets_hoh: tuple
    brackets_mfs: tuple
    
    # SALT Cap
    salt_cap: Decimal
    salt_cap_phaseout_start: Decimal  # AGI where SALT cap starts reducing (OBBBA 2025+)
    
    # Medicare surtax thresholds
    medicare_threshold_mfj: Decimal
    medicare_threshold_mfs: Decimal
    medicare_threshold_other: Decimal
    
    # NIIT thresholds
    niit_threshold_mfj: Decimal
    niit_threshold_mfs: Decimal
    niit_threshold_other: Decimal
    
    # Social Security wage base
    ss_wage_base: Decimal
    
    # HSA limits
    hsa_self: Decimal
    hsa_family: Decimal
    hsa_catchup_55: Decimal
    
    # 401(k) limits
    limit_401k: Decimal
    limit_401k_catchup_50: Decimal
    
    # IRA limits
    limit_ira: Decimal
    limit_ira_catchup_50: Decimal
    
    # Child Tax Credit
    ctc_max: Decimal
    ctc_refundable_max: Decimal
    
    # MA state
    ma_rate: Decimal
    ma_exemption_single: Decimal
    ma_exemption_mfj: Decimal
    ma_exemption_hoh: Decimal
    ma_surtax_threshold: Decimal
    ma_surtax_rate: Decimal


# ============================================================
# TAX YEAR 2024 (Rev. Proc. 2023-34)
# ============================================================

CONSTANTS_2024 = TaxYearConstants(
    year=2024,
    
    std_deduction_single=Decimal("14600"),
    std_deduction_mfj=Decimal("29200"),
    std_deduction_mfs=Decimal("14600"),
    std_deduction_hoh=Decimal("21900"),
    std_deduction_qss=Decimal("29200"),
    additional_std_single_hoh=Decimal("1950"),
    additional_std_mfj_mfs=Decimal("1550"),
    dependent_std_floor=Decimal("1300"),
    dependent_earned_adder=Decimal("450"),
    
    brackets_mfj=(
        (Decimal("23200"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
        (Decimal("94300"),  Decimal("0.12"), Decimal("2320"),      Decimal("23200")),
        (Decimal("201050"), Decimal("0.22"), Decimal("10852"),     Decimal("94300")),
        (Decimal("383900"), Decimal("0.24"), Decimal("34337"),     Decimal("201050")),
        (Decimal("487450"), Decimal("0.32"), Decimal("78221"),     Decimal("383900")),
        (Decimal("731200"), Decimal("0.35"), Decimal("111357"),    Decimal("487450")),
        (None,              Decimal("0.37"), Decimal("196669.50"), Decimal("731200")),
    ),
    brackets_single=(
        (Decimal("11600"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
        (Decimal("47150"),  Decimal("0.12"), Decimal("1160"),      Decimal("11600")),
        (Decimal("100525"), Decimal("0.22"), Decimal("5426"),      Decimal("47150")),
        (Decimal("191950"), Decimal("0.24"), Decimal("17168.50"),  Decimal("100525")),
        (Decimal("243725"), Decimal("0.32"), Decimal("39110.50"),  Decimal("191950")),
        (Decimal("609350"), Decimal("0.35"), Decimal("55678.50"),  Decimal("243725")),
        (None,              Decimal("0.37"), Decimal("183647.25"), Decimal("609350")),
    ),
    brackets_hoh=(
        (Decimal("16550"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
        (Decimal("63100"),  Decimal("0.12"), Decimal("1655"),      Decimal("16550")),
        (Decimal("100500"), Decimal("0.22"), Decimal("7241"),      Decimal("63100")),
        (Decimal("191950"), Decimal("0.24"), Decimal("15469"),     Decimal("100500")),
        (Decimal("243700"), Decimal("0.32"), Decimal("37417"),     Decimal("191950")),
        (Decimal("609350"), Decimal("0.35"), Decimal("53977"),     Decimal("243700")),
        (None,              Decimal("0.37"), Decimal("181954.25"), Decimal("609350")),
    ),
    brackets_mfs=(
        (Decimal("11600"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
        (Decimal("47150"),  Decimal("0.12"), Decimal("1160"),      Decimal("11600")),
        (Decimal("100525"), Decimal("0.22"), Decimal("5426"),      Decimal("47150")),
        (Decimal("191950"), Decimal("0.24"), Decimal("17168.50"),  Decimal("100525")),
        (Decimal("243725"), Decimal("0.32"), Decimal("39110.50"),  Decimal("191950")),
        (Decimal("365600"), Decimal("0.35"), Decimal("55678.50"),  Decimal("243725")),
        (None,              Decimal("0.37"), Decimal("98334.75"),  Decimal("365600")),
    ),
    
    salt_cap=Decimal("10000"),
    salt_cap_phaseout_start=Decimal("999999999"),  # No phaseout in 2024
    
    medicare_threshold_mfj=Decimal("250000"),
    medicare_threshold_mfs=Decimal("125000"),
    medicare_threshold_other=Decimal("200000"),
    
    niit_threshold_mfj=Decimal("250000"),
    niit_threshold_mfs=Decimal("125000"),
    niit_threshold_other=Decimal("200000"),
    
    ss_wage_base=Decimal("168600"),
    
    hsa_self=Decimal("4150"),
    hsa_family=Decimal("8300"),
    hsa_catchup_55=Decimal("1000"),
    
    limit_401k=Decimal("23000"),
    limit_401k_catchup_50=Decimal("7500"),
    
    limit_ira=Decimal("7000"),
    limit_ira_catchup_50=Decimal("1000"),
    
    ctc_max=Decimal("2000"),
    ctc_refundable_max=Decimal("1700"),
    
    ma_rate=Decimal("0.05"),
    ma_exemption_single=Decimal("4400"),
    ma_exemption_mfj=Decimal("8800"),
    ma_exemption_hoh=Decimal("6800"),
    ma_surtax_threshold=Decimal("1000000"),
    ma_surtax_rate=Decimal("0.04"),
)


# ============================================================
# TAX YEAR 2025 (Rev. Proc. 2024-40 + OBBBA)
# ============================================================

CONSTANTS_2025 = TaxYearConstants(
    year=2025,
    
    # OBBBA updated standard deductions
    std_deduction_single=Decimal("15750"),
    std_deduction_mfj=Decimal("31500"),
    std_deduction_mfs=Decimal("15750"),
    std_deduction_hoh=Decimal("23625"),
    std_deduction_qss=Decimal("31500"),
    additional_std_single_hoh=Decimal("2000"),
    additional_std_mfj_mfs=Decimal("1600"),
    dependent_std_floor=Decimal("1350"),
    dependent_earned_adder=Decimal("450"),
    
    brackets_mfj=(
        (Decimal("23850"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
        (Decimal("96950"),  Decimal("0.12"), Decimal("2385"),      Decimal("23850")),
        (Decimal("206700"), Decimal("0.22"), Decimal("11157"),     Decimal("96950")),
        (Decimal("394600"), Decimal("0.24"), Decimal("35302"),     Decimal("206700")),
        (Decimal("501050"), Decimal("0.32"), Decimal("80398"),     Decimal("394600")),
        (Decimal("751600"), Decimal("0.35"), Decimal("114462"),    Decimal("501050")),
        (None,              Decimal("0.37"), Decimal("202154.50"), Decimal("751600")),
    ),
    brackets_single=(
        (Decimal("11925"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
        (Decimal("48475"),  Decimal("0.12"), Decimal("1192.50"),   Decimal("11925")),
        (Decimal("103350"), Decimal("0.22"), Decimal("5578.50"),   Decimal("48475")),
        (Decimal("197300"), Decimal("0.24"), Decimal("17651.50"),  Decimal("103350")),
        (Decimal("250525"), Decimal("0.32"), Decimal("40199.50"),  Decimal("197300")),
        (Decimal("626350"), Decimal("0.35"), Decimal("57231.50"),  Decimal("250525")),
        (None,              Decimal("0.37"), Decimal("188769.75"), Decimal("626350")),
    ),
    brackets_hoh=(
        (Decimal("17000"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
        (Decimal("64850"),  Decimal("0.12"), Decimal("1700"),      Decimal("17000")),
        (Decimal("103350"), Decimal("0.22"), Decimal("7442"),      Decimal("64850")),
        (Decimal("197300"), Decimal("0.24"), Decimal("15912"),     Decimal("103350")),
        (Decimal("250500"), Decimal("0.32"), Decimal("38460"),     Decimal("197300")),
        (Decimal("626350"), Decimal("0.35"), Decimal("55484"),     Decimal("250500")),
        (None,              Decimal("0.37"), Decimal("187031.50"), Decimal("626350")),
    ),
    brackets_mfs=(
        (Decimal("11925"),  Decimal("0.10"), Decimal("0"),         Decimal("0")),
        (Decimal("48475"),  Decimal("0.12"), Decimal("1192.50"),   Decimal("11925")),
        (Decimal("103350"), Decimal("0.22"), Decimal("5578.50"),   Decimal("48475")),
        (Decimal("197300"), Decimal("0.24"), Decimal("17651.50"),  Decimal("103350")),
        (Decimal("250525"), Decimal("0.32"), Decimal("40199.50"),  Decimal("197300")),
        (Decimal("375800"), Decimal("0.35"), Decimal("57231.50"),  Decimal("250525")),
        (None,              Decimal("0.37"), Decimal("101077.75"), Decimal("375800")),
    ),
    
    # OBBBA: SALT cap increased to $40K, phases out at $500K+ AGI
    salt_cap=Decimal("40000"),
    salt_cap_phaseout_start=Decimal("500000"),
    
    medicare_threshold_mfj=Decimal("250000"),
    medicare_threshold_mfs=Decimal("125000"),
    medicare_threshold_other=Decimal("200000"),
    
    niit_threshold_mfj=Decimal("250000"),
    niit_threshold_mfs=Decimal("125000"),
    niit_threshold_other=Decimal("200000"),
    
    ss_wage_base=Decimal("176100"),
    
    hsa_self=Decimal("4300"),
    hsa_family=Decimal("8550"),
    hsa_catchup_55=Decimal("1000"),
    
    limit_401k=Decimal("23500"),
    limit_401k_catchup_50=Decimal("7500"),
    
    limit_ira=Decimal("7000"),
    limit_ira_catchup_50=Decimal("1000"),
    
    # OBBBA: CTC increases to $2,200 in 2026, $2,000 for 2025
    ctc_max=Decimal("2000"),
    ctc_refundable_max=Decimal("1700"),
    
    ma_rate=Decimal("0.05"),
    ma_exemption_single=Decimal("4400"),
    ma_exemption_mfj=Decimal("8800"),
    ma_exemption_hoh=Decimal("6800"),
    ma_surtax_threshold=Decimal("1000000"),
    ma_surtax_rate=Decimal("0.04"),
)


# ============================================================
# Lookup
# ============================================================

_CONSTANTS = {
    2024: CONSTANTS_2024,
    2025: CONSTANTS_2025,
}


def get_constants(year: int) -> TaxYearConstants:
    """Get tax constants for a given year."""
    if year not in _CONSTANTS:
        raise ValueError(f"Tax year {year} not supported. Available: {list(_CONSTANTS.keys())}")
    return _CONSTANTS[year]
