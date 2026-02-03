"""
Tax data models — the core data structures for tax return information.

These models represent the taxpayer's financial data in a structured format
that can be used by the tax engine (Column Tax API or custom) to calculate
taxes and generate IRS-compliant XML for e-filing.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional
from datetime import date


# ============================================================
# Enums
# ============================================================

class FilingStatus(Enum):
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_SURVIVING_SPOUSE = "qualifying_surviving_spouse"


class State(Enum):
    """US states and territories."""
    MA = "MA"
    CA = "CA"
    NY = "NY"
    TX = "TX"
    FL = "FL"
    # ... extend as needed
    # No-income-tax states
    AK = "AK"
    NV = "NV"
    NH = "NH"  # No income tax on wages (tax on interest/dividends)
    SD = "SD"
    TN = "TN"
    WA = "WA"
    WY = "WY"


class IncomeType(Enum):
    W2_WAGES = "w2_wages"
    INTEREST = "interest"
    DIVIDENDS_QUALIFIED = "dividends_qualified"
    DIVIDENDS_ORDINARY = "dividends_ordinary"
    CAPITAL_GAINS_SHORT = "capital_gains_short"
    CAPITAL_GAINS_LONG = "capital_gains_long"
    RENTAL_INCOME = "rental_income"
    SELF_EMPLOYMENT = "self_employment"
    SOCIAL_SECURITY = "social_security"
    RETIREMENT_DISTRIBUTION = "retirement_distribution"
    OTHER = "other"


class DocumentType(Enum):
    W2 = "w2"
    W2_G = "w2_g"
    FORM_1099_INT = "1099_int"
    FORM_1099_DIV = "1099_div"
    FORM_1099_B = "1099_b"
    FORM_1099_R = "1099_r"
    FORM_1099_MISC = "1099_misc"
    FORM_1099_NEC = "1099_nec"
    FORM_1099_G = "1099_g"
    FORM_1099_SA = "1099_sa"
    FORM_1098 = "1098"  # Mortgage interest
    FORM_1098_T = "1098_t"  # Tuition
    FORM_1098_E = "1098_e"  # Student loan interest
    SCHEDULE_K1 = "k1"
    SSA_1099 = "ssa_1099"
    FORM_5498 = "5498"  # IRA contributions
    FORM_5498_SA = "5498_sa"  # HSA contributions
    PRIOR_YEAR_1040 = "prior_1040"
    OTHER = "other"


# ============================================================
# Identity & Personal Info
# ============================================================

@dataclass
class Person:
    """Represents a taxpayer or spouse."""
    first_name: str = ""
    middle_initial: str = ""
    last_name: str = ""
    ssn: str = ""  # Encrypted at rest, never logged
    date_of_birth: Optional[date] = None
    occupation: str = ""
    
    # Contact
    email: str = ""
    phone: str = ""


@dataclass
class Address:
    street: str = ""
    apt: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = "US"


@dataclass
class Dependent:
    first_name: str = ""
    last_name: str = ""
    ssn: str = ""
    date_of_birth: Optional[date] = None
    relationship: str = ""
    months_lived_with: int = 12
    is_student: bool = False
    is_disabled: bool = False


# ============================================================
# Income Documents
# ============================================================

@dataclass
class W2:
    """Form W-2: Wage and Tax Statement"""
    employer_name: str = ""
    employer_ein: str = ""
    employer_address: Optional[Address] = None
    
    # Box 1-20
    wages: Decimal = Decimal("0")                    # Box 1
    federal_tax_withheld: Decimal = Decimal("0")     # Box 2
    social_security_wages: Decimal = Decimal("0")    # Box 3
    social_security_tax: Decimal = Decimal("0")      # Box 4
    medicare_wages: Decimal = Decimal("0")           # Box 5
    medicare_tax: Decimal = Decimal("0")             # Box 6
    social_security_tips: Decimal = Decimal("0")     # Box 7
    allocated_tips: Decimal = Decimal("0")           # Box 8
    # Box 9 is blank
    dependent_care_benefits: Decimal = Decimal("0")  # Box 10
    nonqualified_plans: Decimal = Decimal("0")       # Box 11
    # Box 12: coded items (retirement, HSA, etc.)
    box_12_codes: dict = field(default_factory=dict)  # e.g. {"DD": 5000, "W": 3000}
    # Box 13: checkboxes
    statutory_employee: bool = False
    retirement_plan: bool = False
    third_party_sick_pay: bool = False
    # Box 14: Other
    box_14_other: dict = field(default_factory=dict)
    # State info
    state: str = ""
    state_employer_id: str = ""
    state_wages: Decimal = Decimal("0")              # Box 16
    state_tax_withheld: Decimal = Decimal("0")       # Box 17
    local_wages: Decimal = Decimal("0")              # Box 18
    local_tax_withheld: Decimal = Decimal("0")       # Box 19
    locality_name: str = ""                          # Box 20


@dataclass
class Form1099INT:
    """Form 1099-INT: Interest Income"""
    payer_name: str = ""
    payer_tin: str = ""
    interest_income: Decimal = Decimal("0")           # Box 1
    early_withdrawal_penalty: Decimal = Decimal("0")  # Box 2
    us_savings_bond_interest: Decimal = Decimal("0")  # Box 3
    federal_tax_withheld: Decimal = Decimal("0")      # Box 4
    investment_expenses: Decimal = Decimal("0")       # Box 5
    foreign_tax_paid: Decimal = Decimal("0")          # Box 6
    tax_exempt_interest: Decimal = Decimal("0")       # Box 8
    private_activity_bond: Decimal = Decimal("0")     # Box 9
    market_discount: Decimal = Decimal("0")           # Box 10
    bond_premium: Decimal = Decimal("0")              # Box 11
    state: str = ""
    state_tax_withheld: Decimal = Decimal("0")


@dataclass
class Form1099DIV:
    """Form 1099-DIV: Dividends and Distributions"""
    payer_name: str = ""
    payer_tin: str = ""
    ordinary_dividends: Decimal = Decimal("0")        # Box 1a
    qualified_dividends: Decimal = Decimal("0")       # Box 1b
    total_capital_gain: Decimal = Decimal("0")        # Box 2a
    unrecap_sec_1250: Decimal = Decimal("0")          # Box 2b
    section_1202_gain: Decimal = Decimal("0")         # Box 2c
    collectibles_gain: Decimal = Decimal("0")         # Box 2d
    section_897_ordinary: Decimal = Decimal("0")      # Box 2e
    section_897_capital: Decimal = Decimal("0")       # Box 2f
    nondividend_distributions: Decimal = Decimal("0") # Box 3
    federal_tax_withheld: Decimal = Decimal("0")      # Box 4
    investment_expenses: Decimal = Decimal("0")       # Box 5
    foreign_tax_paid: Decimal = Decimal("0")          # Box 7
    foreign_country: str = ""                         # Box 8
    cash_liquidation: Decimal = Decimal("0")          # Box 9
    noncash_liquidation: Decimal = Decimal("0")       # Box 10
    exempt_interest_dividends: Decimal = Decimal("0") # Box 12
    private_activity_bond: Decimal = Decimal("0")     # Box 13
    state: str = ""
    state_tax_withheld: Decimal = Decimal("0")


@dataclass 
class Form1099B:
    """Form 1099-B: Proceeds from Broker Transactions (single transaction)"""
    broker_name: str = ""
    description: str = ""
    date_acquired: Optional[date] = None
    date_sold: Optional[date] = None
    proceeds: Decimal = Decimal("0")                 # Box 1d
    cost_basis: Decimal = Decimal("0")               # Box 1e
    accrued_market_discount: Decimal = Decimal("0")  # Box 1f
    wash_sale_loss: Decimal = Decimal("0")            # Box 1g
    is_short_term: bool = True
    basis_reported_to_irs: bool = True               # Box 12
    gain_loss: Decimal = Decimal("0")                # Calculated


@dataclass
class Form1098:
    """Form 1098: Mortgage Interest Statement"""
    lender_name: str = ""
    mortgage_interest: Decimal = Decimal("0")        # Box 1
    points_paid: Decimal = Decimal("0")              # Box 2
    mortgage_principal: Decimal = Decimal("0")        # Box 2 (outstanding)
    refund_of_overpaid_interest: Decimal = Decimal("0")  # Box 3
    pmi_premiums: Decimal = Decimal("0")              # Box 5
    property_address: Optional[Address] = None
    acquisition_date: Optional[date] = None
    mortgage_origination_date: Optional[date] = None


# ============================================================
# Deductions & Credits
# ============================================================

@dataclass
class ItemizedDeductions:
    """Schedule A: Itemized Deductions"""
    # Medical
    medical_expenses: Decimal = Decimal("0")
    
    # Taxes (SALT)
    state_income_tax: Decimal = Decimal("0")
    real_estate_tax: Decimal = Decimal("0")
    personal_property_tax: Decimal = Decimal("0")
    # SALT cap: $10,000 for 2025
    
    # Interest
    home_mortgage_interest: Decimal = Decimal("0")
    investment_interest: Decimal = Decimal("0")
    
    # Charity
    cash_contributions: Decimal = Decimal("0")
    noncash_contributions: Decimal = Decimal("0")
    carryover_contributions: Decimal = Decimal("0")
    
    # Other
    casualty_losses: Decimal = Decimal("0")  # Only federally declared disasters
    other_deductions: Decimal = Decimal("0")


@dataclass
class HSAInfo:
    """Form 8889: HSA Information"""
    plan_type: str = "family"  # "self" or "family"
    contributions_employer: Decimal = Decimal("0")
    contributions_personal: Decimal = Decimal("0")
    distributions_total: Decimal = Decimal("0")
    distributions_qualified: Decimal = Decimal("0")
    prior_year_excess: Decimal = Decimal("0")
    account_balance_eoy: Decimal = Decimal("0")


@dataclass
class RetirementContributions:
    """Retirement account contributions for the tax year."""
    traditional_401k: Decimal = Decimal("0")
    roth_401k: Decimal = Decimal("0")
    traditional_ira: Decimal = Decimal("0")
    roth_ira: Decimal = Decimal("0")
    sep_ira: Decimal = Decimal("0")
    simple_ira: Decimal = Decimal("0")
    employer_match_401k: Decimal = Decimal("0")
    after_tax_401k: Decimal = Decimal("0")  # Mega backdoor Roth source


# ============================================================
# Rental Property (Schedule E)
# ============================================================

@dataclass
class RentalProperty:
    """Schedule E: Rental Real Estate"""
    address: Optional[Address] = None
    property_type: str = "single_family"  # single_family, multi_family, condo, etc.
    days_rented: int = 365
    days_personal_use: int = 0
    
    # Income
    rental_income: Decimal = Decimal("0")
    
    # Expenses
    advertising: Decimal = Decimal("0")
    auto_travel: Decimal = Decimal("0")
    cleaning_maintenance: Decimal = Decimal("0")
    commissions: Decimal = Decimal("0")
    insurance: Decimal = Decimal("0")
    legal_professional: Decimal = Decimal("0")
    management_fees: Decimal = Decimal("0")
    mortgage_interest: Decimal = Decimal("0")
    other_interest: Decimal = Decimal("0")
    repairs: Decimal = Decimal("0")
    supplies: Decimal = Decimal("0")
    taxes: Decimal = Decimal("0")
    utilities: Decimal = Decimal("0")
    depreciation: Decimal = Decimal("0")
    other_expenses: Decimal = Decimal("0")
    
    # Depreciation details
    purchase_price: Decimal = Decimal("0")
    land_value: Decimal = Decimal("0")
    purchase_date: Optional[date] = None
    depreciation_method: str = "straight_line"
    useful_life_years: Decimal = Decimal("27.5")
    prior_depreciation: Decimal = Decimal("0")
    
    @property
    def depreciable_basis(self) -> Decimal:
        return self.purchase_price - self.land_value
    
    @property
    def annual_depreciation(self) -> Decimal:
        if self.useful_life_years > 0:
            return self.depreciable_basis / self.useful_life_years
        return Decimal("0")
    
    @property
    def net_rental_income(self) -> Decimal:
        total_expenses = (
            self.advertising + self.auto_travel + self.cleaning_maintenance +
            self.commissions + self.insurance + self.legal_professional +
            self.management_fees + self.mortgage_interest + self.other_interest +
            self.repairs + self.supplies + self.taxes + self.utilities +
            self.depreciation + self.other_expenses
        )
        return self.rental_income - total_expenses


# ============================================================
# Capital Gains (Schedule D / Form 8949)
# ============================================================

@dataclass
class CapitalGainsSummary:
    """Summary of capital gains/losses from Form 8949 → Schedule D"""
    short_term_proceeds: Decimal = Decimal("0")
    short_term_basis: Decimal = Decimal("0")
    short_term_wash_sales: Decimal = Decimal("0")
    long_term_proceeds: Decimal = Decimal("0")
    long_term_basis: Decimal = Decimal("0")
    long_term_wash_sales: Decimal = Decimal("0")
    carryover_loss: Decimal = Decimal("0")  # From prior years
    
    transactions: list = field(default_factory=list)  # List of Form1099B
    
    @property
    def short_term_gain(self) -> Decimal:
        return self.short_term_proceeds - self.short_term_basis + self.short_term_wash_sales
    
    @property
    def long_term_gain(self) -> Decimal:
        return self.long_term_proceeds - self.long_term_basis + self.long_term_wash_sales
    
    @property
    def net_gain(self) -> Decimal:
        return self.short_term_gain + self.long_term_gain + self.carryover_loss


# ============================================================
# The Tax Return — Master Container
# ============================================================

@dataclass
class TaxReturn:
    """
    Complete tax return data for a single tax year.
    This is the master data structure that flows through the entire system.
    """
    # Tax year
    tax_year: int = 2025
    
    # Filing info
    filing_status: FilingStatus = FilingStatus.MARRIED_FILING_JOINTLY
    
    # People
    taxpayer: Person = field(default_factory=Person)
    spouse: Optional[Person] = None
    address: Address = field(default_factory=Address)
    dependents: list[Dependent] = field(default_factory=list)
    
    # Income documents
    w2s: list[W2] = field(default_factory=list)
    forms_1099_int: list[Form1099INT] = field(default_factory=list)
    forms_1099_div: list[Form1099DIV] = field(default_factory=list)
    forms_1099_b: list[Form1099B] = field(default_factory=list)
    forms_1098: list[Form1098] = field(default_factory=list)
    
    # Deductions
    itemized_deductions: Optional[ItemizedDeductions] = None
    use_standard_deduction: bool = True
    
    # Retirement & HSA
    hsa: Optional[HSAInfo] = None
    retirement: Optional[RetirementContributions] = None
    
    # Rental properties
    rental_properties: list[RentalProperty] = field(default_factory=list)
    
    # Capital gains
    capital_gains: Optional[CapitalGainsSummary] = None
    
    # State
    state: State = State.MA
    
    # Payments & withholding
    estimated_tax_payments: Decimal = Decimal("0")
    extension_payment: Decimal = Decimal("0")
    
    # Bank info for refund/payment
    bank_routing: str = ""
    bank_account: str = ""
    bank_account_type: str = "checking"  # checking or savings
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    status: str = "draft"  # draft, review, filed, accepted, rejected
    
    # ---- Computed Properties ----
    
    @property
    def total_w2_wages(self) -> Decimal:
        return sum((w.wages for w in self.w2s), Decimal("0"))
    
    @property
    def total_federal_withholding(self) -> Decimal:
        w2_withholding = sum((w.federal_tax_withheld for w in self.w2s), Decimal("0"))
        int_withholding = sum((f.federal_tax_withheld for f in self.forms_1099_int), Decimal("0"))
        div_withholding = sum((f.federal_tax_withheld for f in self.forms_1099_div), Decimal("0"))
        return w2_withholding + int_withholding + div_withholding
    
    @property
    def total_interest_income(self) -> Decimal:
        return sum((f.interest_income for f in self.forms_1099_int), Decimal("0"))
    
    @property
    def total_dividend_income(self) -> Decimal:
        return sum((f.ordinary_dividends for f in self.forms_1099_div), Decimal("0"))
    
    @property
    def total_qualified_dividends(self) -> Decimal:
        return sum((f.qualified_dividends for f in self.forms_1099_div), Decimal("0"))
    
    @property 
    def total_rental_income(self) -> Decimal:
        return sum((r.net_rental_income for r in self.rental_properties), Decimal("0"))
    
    @property
    def gross_income(self) -> Decimal:
        """Total gross income before adjustments."""
        return (
            self.total_w2_wages +
            self.total_interest_income +
            self.total_dividend_income +
            (self.capital_gains.net_gain if self.capital_gains else Decimal("0")) +
            self.total_rental_income
        )
