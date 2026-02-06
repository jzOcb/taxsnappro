"""
IRS Form 1040 PDF Filler

Fills in the official IRS Form 1040 PDF with user tax data.
Based on 2024 Form 1040 field mapping.
"""

from pypdf import PdfReader, PdfWriter
from pathlib import Path
from typing import Dict, Any, Optional
import io


# 2024 Form 1040 Field Mapping
# Based on IRS f1040.pdf field names
FORM_1040_FIELDS = {
    # === PAGE 1 - Header ===
    "first_name": "topmostSubform[0].Page1[0].f1_01[0]",
    "last_name": "topmostSubform[0].Page1[0].f1_02[0]",
    "ssn": "topmostSubform[0].Page1[0].f1_03[0]",
    "spouse_first_name": "topmostSubform[0].Page1[0].f1_04[0]",
    "spouse_last_name": "topmostSubform[0].Page1[0].f1_05[0]",
    "spouse_ssn": "topmostSubform[0].Page1[0].f1_06[0]",
    
    # Address
    "address_street": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_20[0]",
    "address_apt": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_21[0]",
    "address_city": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_22[0]",
    "address_state": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_23[0]",
    "address_zip": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_24[0]",
    "address_foreign_country": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_25[0]",
    "address_foreign_province": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_26[0]",
    "address_foreign_postal": "topmostSubform[0].Page1[0].Address_ReadOrder[0].f1_27[0]",
    
    # Filing Status Checkboxes
    "filing_single": "topmostSubform[0].Page1[0].c1_1[0]",
    "filing_mfj": "topmostSubform[0].Page1[0].c1_2[0]",
    "filing_mfs": "topmostSubform[0].Page1[0].c1_3[0]",
    "filing_hoh": "topmostSubform[0].Page1[0].c1_4[0]",
    "filing_qss": "topmostSubform[0].Page1[0].c1_5[0]",
    
    # === PAGE 1 - Income (Lines 1-15) ===
    # Line 1: Wages
    "line_1a": "topmostSubform[0].Page1[0].f1_47[0]",  # 1a Total W-2 wages
    "line_1b": "topmostSubform[0].Page1[0].f1_48[0]",  # 1b Household employee wages
    "line_1c": "topmostSubform[0].Page1[0].f1_49[0]",  # 1c Tip income
    "line_1d": "topmostSubform[0].Page1[0].f1_50[0]",  # 1d Medicaid waiver
    "line_1e": "topmostSubform[0].Page1[0].f1_51[0]",  # 1e Taxable dependent care
    "line_1f": "topmostSubform[0].Page1[0].f1_52[0]",  # 1f Employer provided adoption
    "line_1g": "topmostSubform[0].Page1[0].f1_53[0]",  # 1g Form 8919 wages
    "line_1h": "topmostSubform[0].Page1[0].f1_54[0]",  # 1h Other earned income
    "line_1i": "topmostSubform[0].Page1[0].f1_55[0]",  # 1i Nontaxable combat pay
    "line_1z": "topmostSubform[0].Page1[0].f1_56[0]",  # 1z Total (add 1a-1h)
    
    # Line 2: Interest
    "line_2a": "topmostSubform[0].Page1[0].f1_57[0]",  # 2a Tax-exempt interest
    "line_2b": "topmostSubform[0].Page1[0].f1_58[0]",  # 2b Taxable interest
    
    # Line 3: Dividends
    "line_3a": "topmostSubform[0].Page1[0].f1_59[0]",  # 3a Qualified dividends
    "line_3b": "topmostSubform[0].Page1[0].f1_60[0]",  # 3b Ordinary dividends
    
    # Line 4: IRA distributions
    "line_4a": "topmostSubform[0].Page1[0].f1_61[0]",  # 4a IRA distributions
    "line_4b": "topmostSubform[0].Page1[0].f1_62[0]",  # 4b Taxable amount
    
    # Line 5: Pensions
    "line_5a": "topmostSubform[0].Page1[0].f1_63[0]",  # 5a Pensions/annuities
    "line_5b": "topmostSubform[0].Page1[0].f1_64[0]",  # 5b Taxable amount
    
    # Line 6: Social Security
    "line_6a": "topmostSubform[0].Page1[0].f1_65[0]",  # 6a Social security
    "line_6b": "topmostSubform[0].Page1[0].f1_66[0]",  # 6b Taxable amount
    "line_6c": "topmostSubform[0].Page1[0].c1_32[0]",  # 6c Lump-sum checkbox
    
    # Line 7: Capital gain
    "line_7": "topmostSubform[0].Page1[0].f1_67[0]",   # 7 Capital gain/loss
    "line_7_checkbox": "topmostSubform[0].Page1[0].c1_33[0]",  # Schedule D not required
    
    # Line 8: Other income from Schedule 1
    "line_8": "topmostSubform[0].Page1[0].f1_68[0]",   # 8 Additional income (Schedule 1)
    
    # Line 9: Total income
    "line_9": "topmostSubform[0].Page1[0].f1_69[0]",   # 9 Total income
    
    # Line 10: Adjustments from Schedule 1
    "line_10": "topmostSubform[0].Page1[0].f1_70[0]",  # 10 Adjustments (Schedule 1)
    
    # Line 11: AGI
    "line_11": "topmostSubform[0].Page1[0].f1_71[0]",  # 11 Adjusted gross income
    
    # Line 12: Standard/Itemized deduction
    "line_12": "topmostSubform[0].Page1[0].f1_72[0]",  # 12 Deduction
    "line_12_checkbox": "topmostSubform[0].Page1[0].c1_34[0]",  # Itemized checkbox
    
    # Line 13: QBI deduction
    "line_13": "topmostSubform[0].Page1[0].f1_73[0]",  # 13 Qualified business income deduction
    
    # Line 14: Total deductions
    "line_14": "topmostSubform[0].Page1[0].f1_74[0]",  # 14 Add lines 12 and 13
    
    # Line 15: Taxable income
    "line_15": "topmostSubform[0].Page1[0].f1_75[0]",  # 15 Taxable income
    
    # === PAGE 2 - Tax and Credits ===
    # Line 16: Tax
    "line_16": "topmostSubform[0].Page2[0].f2_01[0]",  # 16 Tax
    "line_16_checkbox_8814": "topmostSubform[0].Page2[0].c2_1[0]",  # Form 8814
    "line_16_checkbox_4972": "topmostSubform[0].Page2[0].c2_2[0]",  # Form 4972
    "line_16_checkbox_other": "topmostSubform[0].Page2[0].c2_3[0]",  # Other
    
    # Line 17: Schedule 2 amount
    "line_17": "topmostSubform[0].Page2[0].f2_02[0]",  # 17 Amount from Schedule 2
    
    # Line 18: Total tax before credits
    "line_18": "topmostSubform[0].Page2[0].f2_03[0]",  # 18 Add lines 16 and 17
    
    # Line 19: Child tax credit
    "line_19": "topmostSubform[0].Page2[0].f2_04[0]",  # 19 Child tax credit
    
    # Line 20: Schedule 3 credits
    "line_20": "topmostSubform[0].Page2[0].f2_05[0]",  # 20 Amount from Schedule 3
    
    # Line 21: Total credits
    "line_21": "topmostSubform[0].Page2[0].f2_06[0]",  # 21 Add lines 19 and 20
    
    # Line 22: Tax minus credits
    "line_22": "topmostSubform[0].Page2[0].f2_07[0]",  # 22 Subtract line 21 from 18
    
    # Line 23: Other taxes from Schedule 2
    "line_23": "topmostSubform[0].Page2[0].f2_08[0]",  # 23 Other taxes (Schedule 2)
    
    # Line 24: Total tax
    "line_24": "topmostSubform[0].Page2[0].f2_09[0]",  # 24 Total tax
    
    # === PAGE 2 - Payments ===
    # Line 25: Withholding
    "line_25a": "topmostSubform[0].Page2[0].f2_10[0]",  # 25a Federal tax withheld from W-2
    "line_25b": "topmostSubform[0].Page2[0].f2_11[0]",  # 25b Federal tax withheld from 1099
    "line_25c": "topmostSubform[0].Page2[0].f2_12[0]",  # 25c Other withholding
    "line_25d": "topmostSubform[0].Page2[0].f2_13[0]",  # 25d Total withholding
    
    # Line 26: Estimated payments
    "line_26": "topmostSubform[0].Page2[0].f2_14[0]",  # 26 Estimated tax payments
    
    # Line 27: EIC
    "line_27": "topmostSubform[0].Page2[0].f2_15[0]",  # 27 Earned income credit
    "line_27_nontaxable_combat": "topmostSubform[0].Page2[0].c2_10[0]",  # Nontaxable combat checkbox
    
    # Line 28: Additional child tax credit
    "line_28": "topmostSubform[0].Page2[0].f2_16[0]",  # 28 Additional child tax credit
    
    # Line 29: American opportunity credit
    "line_29": "topmostSubform[0].Page2[0].f2_17[0]",  # 29 American opportunity credit
    
    # Line 30: Reserved
    "line_30": "topmostSubform[0].Page2[0].f2_18[0]",  # 30 Reserved
    
    # Line 31: Schedule 3 amount
    "line_31": "topmostSubform[0].Page2[0].f2_19[0]",  # 31 Amount from Schedule 3
    
    # Line 32: Total other payments
    "line_32": "topmostSubform[0].Page2[0].f2_20[0]",  # 32 Add lines 27-31
    
    # Line 33: Total payments
    "line_33": "topmostSubform[0].Page2[0].f2_21[0]",  # 33 Total payments
    
    # === PAGE 2 - Refund ===
    # Line 34: Overpayment
    "line_34": "topmostSubform[0].Page2[0].f2_23[0]",  # 34 Overpayment (refund)
    
    # Line 35: Refund amount
    "line_35a": "topmostSubform[0].Page2[0].f2_24[0]",  # 35a Amount to be refunded
    "line_35b_routing": "topmostSubform[0].Page2[0].RoutingNo[0].f2_32[0]",  # Routing number
    "line_35c_account_type_checking": "topmostSubform[0].Page2[0].c2_16[0]",  # Checking
    "line_35c_account_type_savings": "topmostSubform[0].Page2[0].c2_16[1]",   # Savings
    "line_35d_account": "topmostSubform[0].Page2[0].AccountNo[0].f2_33[0]",  # Account number
    
    # Line 36: Apply to estimated tax
    "line_36": "topmostSubform[0].Page2[0].f2_34[0]",  # 36 Applied to next year
    
    # Line 37: Amount owed
    "line_37": "topmostSubform[0].Page2[0].f2_35[0]",  # 37 Amount you owe
    
    # Line 38: Estimated tax penalty
    "line_38": "topmostSubform[0].Page2[0].f2_36[0]",  # 38 Estimated tax penalty
}


def format_currency(value: float) -> str:
    """Format a number as currency string for IRS form (no $ sign, no commas in some fields)."""
    if value == 0:
        return ""
    # IRS forms typically want whole dollars
    return str(int(round(value)))


def format_ssn(ssn: str) -> str:
    """Format SSN for display (XXX-XX-XXXX)."""
    ssn = ''.join(filter(str.isdigit, ssn))
    if len(ssn) == 9:
        return f"{ssn[:3]}-{ssn[3:5]}-{ssn[5:]}"
    return ssn


def fill_form_1040(
    tax_data: Dict[str, Any],
    template_path: str = None,
    output_path: str = None
) -> bytes:
    """
    Fill IRS Form 1040 with tax data.
    
    Args:
        tax_data: Dictionary containing all tax calculation data
        template_path: Path to blank Form 1040 PDF (uses bundled if None)
        output_path: Optional path to save filled PDF
    
    Returns:
        Filled PDF as bytes
    """
    # Get template path
    if template_path is None:
        # Look for template in package or common locations
        possible_paths = [
            Path(__file__).parent.parent.parent / "irs_forms" / "f1040.pdf",
            Path.home() / ".taxsnappro" / "irs_forms" / "f1040.pdf",
            Path("/tmp/f1040.pdf"),
        ]
        for p in possible_paths:
            if p.exists():
                template_path = str(p)
                break
        
        if template_path is None:
            raise FileNotFoundError("Form 1040 template not found. Please download from IRS.")
    
    # Read the template
    reader = PdfReader(template_path)
    writer = PdfWriter()
    
    # Clone the PDF (preserves AcroForm)
    writer.clone_document_from_reader(reader)
    
    # Build field values from tax_data
    field_values = {}
    
    # Personal information
    field_values[FORM_1040_FIELDS["first_name"]] = tax_data.get("first_name", "")
    field_values[FORM_1040_FIELDS["last_name"]] = tax_data.get("last_name", "")
    field_values[FORM_1040_FIELDS["ssn"]] = tax_data.get("ssn", "")
    
    if tax_data.get("spouse_first_name"):
        field_values[FORM_1040_FIELDS["spouse_first_name"]] = tax_data.get("spouse_first_name", "")
        field_values[FORM_1040_FIELDS["spouse_last_name"]] = tax_data.get("spouse_last_name", "")
        field_values[FORM_1040_FIELDS["spouse_ssn"]] = tax_data.get("spouse_ssn", "")
    
    # Address
    field_values[FORM_1040_FIELDS["address_street"]] = tax_data.get("address_street", "")
    field_values[FORM_1040_FIELDS["address_apt"]] = tax_data.get("address_apt", "")
    field_values[FORM_1040_FIELDS["address_city"]] = tax_data.get("address_city", "")
    field_values[FORM_1040_FIELDS["address_state"]] = tax_data.get("address_state", "")
    field_values[FORM_1040_FIELDS["address_zip"]] = tax_data.get("address_zip", "")
    
    # Filing status (checkbox)
    filing_status = tax_data.get("filing_status", "single")
    if filing_status == "single":
        field_values[FORM_1040_FIELDS["filing_single"]] = "/Yes"
    elif filing_status == "married_filing_jointly":
        field_values[FORM_1040_FIELDS["filing_mfj"]] = "/Yes"
    elif filing_status == "married_filing_separately":
        field_values[FORM_1040_FIELDS["filing_mfs"]] = "/Yes"
    elif filing_status == "head_of_household":
        field_values[FORM_1040_FIELDS["filing_hoh"]] = "/Yes"
    elif filing_status == "qualifying_widow":
        field_values[FORM_1040_FIELDS["filing_qss"]] = "/Yes"
    
    # Income Lines
    total_wages = tax_data.get("total_wages", 0)
    field_values[FORM_1040_FIELDS["line_1a"]] = format_currency(total_wages)
    field_values[FORM_1040_FIELDS["line_1z"]] = format_currency(total_wages)
    
    # Interest
    field_values[FORM_1040_FIELDS["line_2a"]] = format_currency(tax_data.get("tax_exempt_interest", 0))
    field_values[FORM_1040_FIELDS["line_2b"]] = format_currency(tax_data.get("total_interest", 0))
    
    # Dividends
    field_values[FORM_1040_FIELDS["line_3a"]] = format_currency(tax_data.get("qualified_dividends", 0))
    field_values[FORM_1040_FIELDS["line_3b"]] = format_currency(tax_data.get("total_dividends", 0))
    
    # Capital gains
    capital_gains = tax_data.get("total_capital_gains", 0)
    field_values[FORM_1040_FIELDS["line_7"]] = format_currency(capital_gains)
    
    # Other income (Schedule 1)
    other_income = (
        tax_data.get("total_other_income", 0) +
        tax_data.get("total_rental_income", 0) +
        tax_data.get("total_business_income", 0)
    )
    if other_income:
        field_values[FORM_1040_FIELDS["line_8"]] = format_currency(other_income)
    
    # Line 9: Total income
    total_income = (
        total_wages +
        tax_data.get("total_interest", 0) +
        tax_data.get("total_dividends", 0) +
        capital_gains +
        other_income
    )
    field_values[FORM_1040_FIELDS["line_9"]] = format_currency(total_income)
    
    # Line 10: Adjustments
    adjustments = tax_data.get("hsa_deduction", 0) + (tax_data.get("self_employment_tax", 0) / 2)
    if adjustments:
        field_values[FORM_1040_FIELDS["line_10"]] = format_currency(adjustments)
    
    # Line 11: AGI
    agi = tax_data.get("adjusted_gross_income", 0)
    field_values[FORM_1040_FIELDS["line_11"]] = format_currency(agi)
    
    # Line 12: Deduction
    total_deductions = tax_data.get("total_deductions", 0)
    standard_deduction = tax_data.get("standard_deduction", 0)
    itemized_deductions = tax_data.get("itemized_deductions", 0)
    
    field_values[FORM_1040_FIELDS["line_12"]] = format_currency(total_deductions)
    if itemized_deductions > standard_deduction:
        field_values[FORM_1040_FIELDS["line_12_checkbox"]] = "/Yes"
    
    # Line 13: QBI
    qbi_deduction = tax_data.get("qbi_deduction", 0)
    if qbi_deduction:
        field_values[FORM_1040_FIELDS["line_13"]] = format_currency(qbi_deduction)
    
    # Line 14: Total deductions
    field_values[FORM_1040_FIELDS["line_14"]] = format_currency(total_deductions + qbi_deduction)
    
    # Line 15: Taxable income
    taxable_income = tax_data.get("taxable_income", 0)
    field_values[FORM_1040_FIELDS["line_15"]] = format_currency(taxable_income)
    
    # === Page 2 ===
    
    # Line 16: Tax
    income_tax = tax_data.get("income_tax", tax_data.get("total_tax", 0))
    field_values[FORM_1040_FIELDS["line_16"]] = format_currency(income_tax)
    
    # Line 17: Schedule 2 (Additional Medicare, SE tax, etc.)
    schedule_2 = tax_data.get("additional_medicare_tax", 0) + tax_data.get("self_employment_tax", 0)
    if schedule_2:
        field_values[FORM_1040_FIELDS["line_17"]] = format_currency(schedule_2)
    
    # Line 18: Total tax before credits
    total_tax_before_credits = income_tax + schedule_2
    field_values[FORM_1040_FIELDS["line_18"]] = format_currency(total_tax_before_credits)
    
    # Line 19: Child tax credit
    child_tax_credit = tax_data.get("child_tax_credit", 0)
    if child_tax_credit:
        field_values[FORM_1040_FIELDS["line_19"]] = format_currency(child_tax_credit)
    
    # Line 21: Total credits
    total_credits = child_tax_credit
    if total_credits:
        field_values[FORM_1040_FIELDS["line_21"]] = format_currency(total_credits)
    
    # Line 22: Tax minus credits
    tax_after_credits = max(0, total_tax_before_credits - total_credits)
    field_values[FORM_1040_FIELDS["line_22"]] = format_currency(tax_after_credits)
    
    # Line 24: Total tax
    total_tax = tax_data.get("total_tax", 0)
    field_values[FORM_1040_FIELDS["line_24"]] = format_currency(total_tax)
    
    # Line 25: Withholding
    total_withholding = tax_data.get("total_withholding", 0)
    field_values[FORM_1040_FIELDS["line_25a"]] = format_currency(total_withholding)
    field_values[FORM_1040_FIELDS["line_25d"]] = format_currency(total_withholding)
    
    # Line 33: Total payments
    field_values[FORM_1040_FIELDS["line_33"]] = format_currency(total_withholding)
    
    # Refund or Amount Owed
    refund_or_owed = total_withholding - total_tax
    if refund_or_owed > 0:
        # Refund
        field_values[FORM_1040_FIELDS["line_34"]] = format_currency(refund_or_owed)
        field_values[FORM_1040_FIELDS["line_35a"]] = format_currency(refund_or_owed)
    elif refund_or_owed < 0:
        # Amount owed
        field_values[FORM_1040_FIELDS["line_37"]] = format_currency(abs(refund_or_owed))
    
    # Update fields
    writer.update_page_form_field_values(writer.pages[0], field_values)
    writer.update_page_form_field_values(writer.pages[1], field_values)
    
    # Output
    if output_path:
        with open(output_path, "wb") as f:
            writer.write(f)
        return None
    else:
        buffer = io.BytesIO()
        writer.write(buffer)
        buffer.seek(0)
        return buffer.getvalue()


def get_tax_data_for_1040(state) -> Dict[str, Any]:
    """Extract tax data from state object for Form 1040 filling."""
    return {
        # Personal info (to be added to state)
        "first_name": getattr(state, "first_name", ""),
        "last_name": getattr(state, "last_name", ""),
        "ssn": getattr(state, "ssn", ""),
        "spouse_first_name": getattr(state, "spouse_first_name", ""),
        "spouse_last_name": getattr(state, "spouse_last_name", ""),
        "spouse_ssn": getattr(state, "spouse_ssn", ""),
        "address_street": getattr(state, "address_street", ""),
        "address_apt": getattr(state, "address_apt", ""),
        "address_city": getattr(state, "address_city", ""),
        "address_state": getattr(state, "address_state", ""),
        "address_zip": getattr(state, "address_zip", ""),
        
        # Tax data
        "filing_status": getattr(state, "filing_status", "single"),
        "tax_year": getattr(state, "tax_year", 2024),
        "total_wages": getattr(state, "total_wages", 0),
        "total_interest": getattr(state, "total_interest", 0),
        "total_dividends": getattr(state, "total_dividends", 0),
        "qualified_dividends": getattr(state, "qualified_dividends", 0),
        "total_capital_gains": getattr(state, "total_capital_gains", 0),
        "total_other_income": getattr(state, "total_other_income", 0),
        "total_rental_income": getattr(state, "total_rental_income", 0),
        "total_business_income": getattr(state, "total_business_income", 0),
        "hsa_deduction": getattr(state, "hsa_deduction", 0),
        "self_employment_tax": getattr(state, "self_employment_tax", 0),
        "adjusted_gross_income": getattr(state, "adjusted_gross_income", 0),
        "standard_deduction": getattr(state, "standard_deduction", 0),
        "itemized_deductions": getattr(state, "itemized_deductions", 0),
        "total_deductions": getattr(state, "total_deductions", 0),
        "qbi_deduction": getattr(state, "qbi_deduction", 0),
        "taxable_income": getattr(state, "taxable_income", 0),
        "income_tax": getattr(state, "income_tax", 0),
        "total_tax": getattr(state, "total_tax", 0),
        "additional_medicare_tax": getattr(state, "additional_medicare_tax", 0),
        "child_tax_credit": getattr(state, "child_tax_credit", 0),
        "total_withholding": getattr(state, "total_withholding", 0),
    }
