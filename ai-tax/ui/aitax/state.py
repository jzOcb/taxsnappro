"""
TaxForge - Application State
"""
import reflex as rx
import os
from pathlib import Path
from typing import List, Dict
from enum import Enum

from .document_extractor import (
    extract_with_retry, 
    convert_to_w2, 
    convert_to_1099, 
    convert_to_business_income,
    convert_1099_misc_to_other_income,
    REQUEST_DELAY_SECONDS
)
from .persistence import save_state, load_state, clear_saved_data
import asyncio


class FilingStatus(str, Enum):
    """Filing status enum."""
    SINGLE = "single"
    MARRIED_FILING_JOINTLY = "married_filing_jointly"
    MARRIED_FILING_SEPARATELY = "married_filing_separately"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    QUALIFYING_WIDOW = "qualifying_widow"


# 2024 Tax Constants
TAX_CONSTANTS_2024 = {
    "standard_deduction": {
        "single": 14600,
        "married_filing_jointly": 29200,
        "married_filing_separately": 14600,
        "head_of_household": 21900,
        "qualifying_widow": 29200,
    },
    # 2024 Federal Income Tax Brackets (marginal rates)
    "brackets": {
        "single": [
            (11600, 0.10),
            (47150, 0.12),
            (100525, 0.22),
            (191950, 0.24),
            (243725, 0.32),
            (609350, 0.35),
            (float('inf'), 0.37),
        ],
        "married_filing_jointly": [
            (23200, 0.10),
            (94300, 0.12),
            (201050, 0.22),
            (383900, 0.24),
            (487450, 0.32),
            (731200, 0.35),
            (float('inf'), 0.37),
        ],
        "married_filing_separately": [
            (11600, 0.10),
            (47150, 0.12),
            (100525, 0.22),
            (191950, 0.24),
            (243725, 0.32),
            (365600, 0.35),
            (float('inf'), 0.37),
        ],
        "head_of_household": [
            (16550, 0.10),
            (63100, 0.12),
            (100500, 0.22),
            (191950, 0.24),
            (243700, 0.32),
            (609350, 0.35),
            (float('inf'), 0.37),
        ],
        "qualifying_widow": [
            (23200, 0.10),
            (94300, 0.12),
            (201050, 0.22),
            (383900, 0.24),
            (487450, 0.32),
            (731200, 0.35),
            (float('inf'), 0.37),
        ],
    },
    # 2024 Long-term Capital Gains Tax Brackets
    "capital_gains_brackets": {
        "single": [
            (47025, 0.00),   # 0% up to $47,025
            (518900, 0.15),  # 15% up to $518,900
            (float('inf'), 0.20),  # 20% above
        ],
        "married_filing_jointly": [
            (94050, 0.00),
            (583750, 0.15),
            (float('inf'), 0.20),
        ],
    },
}


class TaxAppState(rx.State):
    """Main application state."""
    
    # ===== UI State =====
    processing: bool = False
    processing_file_index: int = 0
    processing_total_files: int = 0
    processing_current_file: str = ""
    error_message: str = ""
    success_message: str = ""
    show_api_modal: bool = False  # API key configuration modal
    temp_api_key: str = ""  # Temporary input for modal
    
    # ===== User Settings =====
    tax_year: int = 2024
    filing_status: str = "single"
    openai_api_key: str = ""  # Actually Gemini API key
    anthropic_api_key: str = ""  # Alias
    settings_api_key_input: str = ""  # Temp input for settings page
    settings_dirty: bool = False  # Track unsaved changes
    
    # ===== Form Inputs for Manual Entry =====
    # Rental property form
    rental_form_address: str = ""
    rental_form_income: str = ""
    rental_form_mortgage: str = ""
    rental_form_tax: str = ""
    rental_form_insurance: str = ""
    rental_form_repairs: str = ""
    rental_form_depreciation: str = ""
    rental_form_other: str = ""
    
    # Business form
    business_form_name: str = ""
    business_form_income: str = ""
    business_form_expenses: str = ""
    
    # Other income/deduction forms
    other_income_form_desc: str = ""
    other_income_form_amount: str = ""
    other_deduction_form_desc: str = ""
    other_deduction_form_amount: str = ""
    
    # Dependent form
    dependent_form_name: str = ""
    dependent_form_relationship: str = ""
    dependent_form_age: str = ""
    child_care_form_amount: str = ""
    
    # Form visibility
    show_rental_form: bool = False
    show_business_form: bool = False
    show_other_income_form: bool = False
    show_other_deduction_form: bool = False
    show_dependent_form: bool = False
    
    # ===== Document State =====
    uploaded_files: List[str] = []
    parsed_documents: List[Dict] = []  # {name, type, status: pending|processing|parsed|error}
    selected_files: List[str] = []  # Files selected for processing
    
    # ===== Personal Info =====
    first_name: str = ""
    last_name: str = ""
    
    # ===== Tax Data =====
    w2_list: List[Dict] = []
    form_1099_list: List[Dict] = []
    form_1098_list: List[Dict] = []  # Mortgage interest (deduction)
    form_5498_list: List[Dict] = []  # HSA contributions (deduction)
    
    # ===== Manual Entry Data =====
    # Schedule E - Rental Property (multiple properties)
    rental_properties: List[Dict] = []  # {address, rent_income, expenses: {mortgage_interest, property_tax, insurance, repairs, management, utilities, depreciation, other}}
    
    # Schedule C - Business Income (simplified)
    business_income: List[Dict] = []  # {name, gross_income, expenses, net_profit}
    
    # Other manual entries
    other_income: List[Dict] = []  # {description, amount, tax_type}
    other_deductions: List[Dict] = []  # {description, amount, deduction_type}
    
    # Dependents
    dependents: List[Dict] = []  # {name, relationship, age, ssn_last4, is_child}
    
    # Child and Dependent Care
    child_care_expenses: float = 0.0  # Expenses for dependent care while working
    
    # ===== Calculated Values =====
    total_wages: float = 0.0
    total_interest: float = 0.0
    total_dividends: float = 0.0
    total_capital_gains: float = 0.0  # From 1099-B (long-term)
    total_rental_income: float = 0.0  # Schedule E net income
    total_business_income: float = 0.0  # Schedule C net profit
    total_other_income: float = 0.0
    hsa_deduction: float = 0.0  # From 5498-SA
    self_employment_tax: float = 0.0  # SE tax on business income
    mortgage_interest_deduction: float = 0.0  # From 1098
    adjusted_gross_income: float = 0.0
    itemized_deductions: float = 0.0
    standard_deduction: float = 0.0
    total_deductions: float = 0.0  # Higher of standard or itemized
    capital_gains_tax: float = 0.0  # Separate tax on capital gains
    additional_medicare_tax: float = 0.0  # 0.9% on wages > $250k (MFJ)
    niit: float = 0.0  # Net Investment Income Tax 3.8%
    
    # Tax Credits
    child_tax_credit: float = 0.0  # $2,000 per child under 17
    other_dependent_credit: float = 0.0  # $500 per other dependent
    child_care_credit: float = 0.0  # Credit for child/dependent care
    total_credits: float = 0.0
    taxable_income: float = 0.0
    total_tax: float = 0.0
    total_withholding: float = 0.0
    other_withholding: float = 0.0  # From 1099-NEC/MISC Box 4 (goes to Line 25c)
    refund_or_owed: float = 0.0
    is_refund: bool = True
    
    # ===== Return State =====
    return_status: str = "not_started"
    return_generated: bool = False
    
    # ===== Methods =====
    
    def set_filing_status(self, status: str):
        """Update filing status."""
        self.filing_status = status
        self._recalculate()
    
    def set_api_key(self, key: str):
        """Set Gemini API key directly (for modal)."""
        self.openai_api_key = key
    
    def set_settings_api_key(self, key: str):
        """Set API key input on settings page (not saved yet)."""
        self.settings_api_key_input = key
        self.settings_dirty = True
    
    def load_settings(self):
        """Load current values into settings inputs."""
        self.settings_api_key_input = self.openai_api_key
        self.settings_dirty = False
    
    def save_settings(self):
        """Save settings from input fields."""
        self.openai_api_key = self.settings_api_key_input
        self.settings_dirty = False
        self.success_message = "Settings saved!"
    
    def set_temp_api_key(self, key: str):
        """Set temporary API key in modal."""
        self.temp_api_key = key
    
    def open_api_modal(self):
        """Open API key modal."""
        self.temp_api_key = self.openai_api_key
        self.show_api_modal = True
    
    def close_api_modal(self):
        """Close API key modal."""
        self.show_api_modal = False
        self.temp_api_key = ""
    
    def save_api_key_from_modal(self):
        """Save API key from modal and close."""
        self.openai_api_key = self.temp_api_key
        self.show_api_modal = False
        self.success_message = "API key saved!"
        self._auto_save()  # Persist API key
    
    def check_api_key_for_upload(self):
        """Check if API key is set, open modal if not."""
        if not self.openai_api_key:
            self.open_api_modal()
            return False
        return True
    
    @rx.var
    def has_api_key(self) -> bool:
        """Check if API key is configured."""
        return bool(self.openai_api_key)
    
    @rx.var
    def processing_progress(self) -> str:
        """Get processing progress message."""
        if not self.processing:
            return ""
        if self.processing_total_files == 0:
            return "Preparing..."
        return f"Processing {self.processing_file_index}/{self.processing_total_files}: {self.processing_current_file}"
    
    async def handle_file_upload(self, files: List[rx.UploadFile]):
        """Handle uploaded tax documents - just save, no AI processing."""
        self.error_message = ""
        self.success_message = ""
        
        # Ensure upload directory exists
        upload_dir = Path("uploaded_files")
        upload_dir.mkdir(exist_ok=True)
        
        new_files = 0
        try:
            for file in files:
                file_data = await file.read()
                filename = file.filename
                
                # Skip if already uploaded
                if filename in self.uploaded_files:
                    continue
                
                # Save file to disk
                file_path = upload_dir / filename
                file_path.write_bytes(file_data)
                
                self.uploaded_files.append(filename)
                
                # Initial doc type guess from filename
                doc_type = self._detect_document_type(filename)
                self.parsed_documents.append({
                    "name": filename,
                    "type": doc_type,
                    "status": "pending",  # Not processed yet
                    "included": True,  # Include in tax calculation by default
                })
                new_files += 1
            
            if new_files > 0:
                self.success_message = f"Uploaded {new_files} file(s). Go to Review to process with AI."
                self.return_status = "in_progress"
                self._auto_save()  # Persist uploaded files list
        except Exception as e:
            self.error_message = f"Upload failed: {str(e)}"
    
    def toggle_file_selection(self, filename: str):
        """Toggle file selection for AI processing."""
        # Don't allow selecting already-processed files
        for doc in self.parsed_documents:
            if doc["name"] == filename and doc["status"] == "parsed":
                return
        
        if filename in self.selected_files:
            self.selected_files.remove(filename)
        else:
            self.selected_files.append(filename)
    
    def select_all_pending(self):
        """Select all pending files for processing."""
        self.selected_files = [
            doc["name"] for doc in self.parsed_documents 
            if doc["status"] in ("pending", "error")
        ]
    
    def clear_selection(self):
        """Clear file selection."""
        self.selected_files = []
    
    def toggle_document_inclusion(self, filename: str):
        """Toggle whether a parsed document is included in tax calculation."""
        for doc in self.parsed_documents:
            if doc["name"] == filename and doc["status"] == "parsed":
                doc["included"] = not doc.get("included", True)
                self._recalculate()  # Recalculate totals based on new inclusion
                self._auto_save()
                return
    
    def get_included_files(self) -> set:
        """Get set of filenames that are included in calculation."""
        return {
            doc["name"] for doc in self.parsed_documents 
            if doc.get("status") == "parsed" and doc.get("included", True)
        }
    
    async def process_selected_files(self):
        """Process selected files with AI."""
        if not self.selected_files:
            self.error_message = "No files selected for processing"
            return
        
        if not self.openai_api_key:
            self.error_message = "Please configure your API key in Settings first"
            return
        
        self.processing = True
        self.processing_total_files = len(self.selected_files)
        self.processing_file_index = 0
        self.error_message = ""
        self.success_message = ""
        yield  # Trigger UI update to show processing overlay
        
        upload_dir = Path("uploaded_files")
        parsed_count = 0
        error_files = []
        
        try:
            for idx, filename in enumerate(self.selected_files):
                self.processing_file_index = idx + 1
                self.processing_current_file = filename
                
                # Update status to processing
                for doc in self.parsed_documents:
                    if doc["name"] == filename:
                        doc["status"] = "processing"
                yield  # Update UI to show current file
                
                file_path = upload_dir / filename
                
                # Call AI to extract data (Gemini) with retry
                result = await extract_with_retry(
                    str(file_path),
                    api_key=self.openai_api_key,
                )
                
                # Add delay between files to avoid rate limiting
                await asyncio.sleep(REQUEST_DELAY_SECONDS)
                
                if result.get("error"):
                    error_files.append(f"{filename}: {result['error']}")
                    for doc in self.parsed_documents:
                        if doc["name"] == filename:
                            doc["status"] = "error"
                    yield  # Update UI to show error status
                    continue
                
                # Update document type from AI
                ai_doc_type = result.get("document_type", "OTHER")
                for doc in self.parsed_documents:
                    if doc["name"] == filename:
                        doc["type"] = ai_doc_type
                        doc["status"] = "parsed"
                
                # Extract and add to appropriate list
                extracted = result.get("extracted_data", {})
                
                # Remove any existing entries from this file (prevent duplicates on re-process)
                self.w2_list = [w for w in self.w2_list if w.get("source_file") != filename]
                self.form_1099_list = [f for f in self.form_1099_list if f.get("source_file") != filename]
                self.form_1098_list = [f for f in self.form_1098_list if f.get("source_file") != filename]
                self.form_5498_list = [f for f in self.form_5498_list if f.get("source_file") != filename]
                self.business_income = [b for b in self.business_income if b.get("source_file") != filename]
                self.other_income = [o for o in self.other_income if o.get("source_file") != filename]
                self.rental_properties = [r for r in self.rental_properties if r.get("source_file") != filename]
                
                if ai_doc_type == "W-2":
                    w2_data = convert_to_w2(extracted)
                    w2_data["source_file"] = filename  # Track source
                    self.w2_list.append(w2_data)
                    parsed_count += 1
                    
                elif ai_doc_type in ("1099-INT", "1099-DIV", "1099-B"):
                    form_data = convert_to_1099(extracted, ai_doc_type)
                    form_data["source_file"] = filename  # Track source
                    self.form_1099_list.append(form_data)
                    parsed_count += 1
                    
                elif ai_doc_type == "1098":
                    # Mortgage interest is a DEDUCTION, not income
                    self.form_1098_list.append({
                        "lender_name": extracted.get("lender_name", "Mortgage Lender"),
                        "mortgage_interest": float(extracted.get("mortgage_interest", 0)),
                        "points_paid": float(extracted.get("points_paid", 0)),
                        "property_taxes": float(extracted.get("property_taxes", 0)),
                        "source_file": filename,
                    })
                    parsed_count += 1
                    
                elif ai_doc_type == "5498-SA":
                    # HSA contribution is a DEDUCTION (above-the-line)
                    self.form_5498_list.append({
                        "trustee_name": extracted.get("trustee_name", "HSA Administrator"),
                        "contribution": float(extracted.get("contribution", 0)),
                        "source_file": filename,
                    })
                    parsed_count += 1
                
                elif ai_doc_type == "1099-NEC":
                    # Nonemployee compensation → Schedule C (self-employment)
                    business_data = convert_to_business_income(extracted, "1099-NEC")
                    business_data["source_file"] = filename
                    self.business_income.append(business_data)
                    
                    # Track any withholding
                    withheld = float(extracted.get("federal_withheld", 0))
                    if withheld > 0:
                        # Add to a special 1099 withholding tracker (goes to Line 25c)
                        if not hasattr(self, 'other_withholding'):
                            self.other_withholding = 0.0
                        self.other_withholding += withheld
                    parsed_count += 1
                
                elif ai_doc_type == "1099-MISC":
                    # Check if it has nonemployee comp (Box 7, pre-2020)
                    nec_amount = float(extracted.get("nonemployee_compensation", 0))
                    if nec_amount > 0:
                        # Treat like 1099-NEC
                        business_data = convert_to_business_income(extracted, "1099-MISC")
                        business_data["source_file"] = filename
                        self.business_income.append(business_data)
                    
                    # Handle other 1099-MISC income (rents, royalties, other)
                    other_entries = convert_1099_misc_to_other_income(extracted)
                    for entry in other_entries:
                        entry["source_file"] = filename
                        if entry.get("category") == "rental":
                            # Add as simple rental (user can expand)
                            self.rental_properties.append({
                                "address": entry["description"],
                                "rent_income": entry["amount"],
                                "mortgage_interest": 0,
                                "property_tax": 0,
                                "insurance": 0,
                                "repairs": 0,
                                "management": 0,
                                "utilities": 0,
                                "depreciation": 0,
                                "other_expenses": 0,
                                "total_expenses": 0,
                                "net_income": entry["amount"],
                                "source_file": filename,
                            })
                        else:
                            # Other income
                            self.other_income.append({
                                "description": entry["description"],
                                "amount": entry["amount"],
                                "source_file": filename,
                            })
                    
                    if nec_amount > 0 or other_entries:
                        parsed_count += 1
            
            # Recalculate totals
            self._recalculate()
            
            self.return_status = "in_progress"
            
            if parsed_count > 0:
                self.success_message = f"Successfully parsed {parsed_count} document(s)"
            if error_files:
                self.error_message = "Errors: " + "; ".join(error_files)
            
            # Clear selection after processing
            self.selected_files = []
            
        except Exception as e:
            self.error_message = f"Upload failed: {str(e)}"
        finally:
            self.processing = False
    
    def _detect_document_type(self, filename: str) -> str:
        """Detect document type from filename."""
        lower = filename.lower()
        if "w2" in lower or "w-2" in lower:
            return "W-2"
        elif "1099-nec" in lower or "1099nec" in lower:
            return "1099-NEC"
        elif "1099-misc" in lower or "1099misc" in lower:
            return "1099-MISC"
        elif "1099-int" in lower or "1099int" in lower:
            return "1099-INT"
        elif "1099-div" in lower or "1099div" in lower:
            return "1099-DIV"
        elif "1099-b" in lower or "1099b" in lower:
            return "1099-B"
        elif "1099" in lower:
            return "1099"
        elif "1098" in lower:
            return "1098"
        elif "5498" in lower:
            return "5498-SA"
        return "Unknown"
    
    def add_w2(self, employer: str, wages: float, withheld: float):
        """Add a W-2 entry."""
        self.w2_list.append({
            "employer_name": employer,
            "wages": wages,
            "federal_withheld": withheld,
        })
        self._recalculate()
    
    def add_1099(self, payer: str, amount: float, form_type: str = "1099-INT"):
        """Add a 1099 entry."""
        self.form_1099_list.append({
            "payer_name": payer,
            "amount": amount,
            "form_type": form_type,
        })
        self._recalculate()
    
    def remove_w2(self, index: int):
        """Remove a W-2 entry."""
        if 0 <= index < len(self.w2_list):
            self.w2_list.pop(index)
            self._recalculate()
    
    def remove_1099(self, index: int):
        """Remove a 1099 entry."""
        if 0 <= index < len(self.form_1099_list):
            self.form_1099_list.pop(index)
            self._recalculate()
    
    # ===== Schedule E - Rental Property Methods =====
    def add_rental_property(self, address: str, rent_income: float, 
                           mortgage_interest: float = 0, property_tax: float = 0,
                           insurance: float = 0, repairs: float = 0, 
                           management: float = 0, utilities: float = 0,
                           depreciation: float = 0, other_expenses: float = 0,
                           monthly_rent: float = 0, quarterly_tax: float = 0):
        """Add a rental property (Schedule E). All values should be annual."""
        total_expenses = (mortgage_interest + property_tax + insurance + 
                         repairs + management + utilities + depreciation + other_expenses)
        self.rental_properties.append({
            "address": address,
            "monthly_rent": monthly_rent,    # For display
            "quarterly_tax": quarterly_tax,  # For display
            "rent_income": rent_income,      # Annual (monthly × 12)
            "mortgage_interest": mortgage_interest,
            "property_tax": property_tax,    # Annual (quarterly × 4)
            "insurance": insurance,
            "repairs": repairs,
            "management": management,
            "utilities": utilities,
            "depreciation": depreciation,
            "other_expenses": other_expenses,
            "total_expenses": total_expenses,
            "net_income": rent_income - total_expenses,
        })
        self._recalculate()
    
    def remove_rental_property(self, index: int):
        """Remove a rental property."""
        if 0 <= index < len(self.rental_properties):
            self.rental_properties.pop(index)
            self._recalculate()
    
    # ===== Schedule C - Business Income Methods =====
    def add_business(self, name: str, gross_income: float, expenses: float):
        """Add a business (Schedule C simplified)."""
        net_profit = gross_income - expenses
        self.business_income.append({
            "name": name,
            "gross_income": gross_income,
            "expenses": expenses,
            "net_profit": net_profit,
        })
        self._recalculate()
    
    def remove_business(self, index: int):
        """Remove a business."""
        if 0 <= index < len(self.business_income):
            self.business_income.pop(index)
            self._recalculate()
    
    # ===== Other Manual Entry Methods =====
    def add_other_income(self, description: str, amount: float):
        """Add other income."""
        self.other_income.append({
            "description": description,
            "amount": amount,
        })
        self._recalculate()
    
    def remove_other_income(self, index: int):
        """Remove other income."""
        if 0 <= index < len(self.other_income):
            self.other_income.pop(index)
            self._recalculate()
    
    def add_other_deduction(self, description: str, amount: float):
        """Add other deduction (above-the-line)."""
        self.other_deductions.append({
            "description": description,
            "amount": amount,
        })
        self._recalculate()
    
    def remove_other_deduction(self, index: int):
        """Remove other deduction."""
        if 0 <= index < len(self.other_deductions):
            self.other_deductions.pop(index)
            self._recalculate()
    
    # ===== Dependent Methods =====
    def add_dependent(self, name: str, relationship: str, age: int, is_child: bool = True):
        """Add a dependent (child or other)."""
        self.dependents.append({
            "name": name,
            "relationship": relationship,
            "age": age,
            "is_child": is_child and age < 17,  # Child Tax Credit requires under 17
        })
        self._recalculate()
    
    def remove_dependent(self, index: int):
        """Remove a dependent."""
        if 0 <= index < len(self.dependents):
            self.dependents.pop(index)
            self._recalculate()
    
    def set_child_care_expenses(self, amount: float):
        """Set child/dependent care expenses."""
        self.child_care_expenses = amount
        self._recalculate()
    
    # ===== Form Toggle Methods =====
    def toggle_rental_form(self):
        self.show_rental_form = not self.show_rental_form
    
    def toggle_business_form(self):
        self.show_business_form = not self.show_business_form
    
    def toggle_other_income_form(self):
        self.show_other_income_form = not self.show_other_income_form
    
    def toggle_other_deduction_form(self):
        self.show_other_deduction_form = not self.show_other_deduction_form
    
    def toggle_dependent_form(self):
        self.show_dependent_form = not self.show_dependent_form
    
    # ===== Form Input Setters =====
    def set_rental_address(self, val): self.rental_form_address = val
    def set_rental_income(self, val): self.rental_form_income = val
    def set_rental_mortgage(self, val): self.rental_form_mortgage = val
    def set_rental_tax(self, val): self.rental_form_tax = val
    def set_rental_insurance(self, val): self.rental_form_insurance = val
    def set_rental_repairs(self, val): self.rental_form_repairs = val
    def set_rental_depreciation(self, val): self.rental_form_depreciation = val
    def set_rental_other(self, val): self.rental_form_other = val
    
    def set_business_name(self, val): self.business_form_name = val
    def set_business_income(self, val): self.business_form_income = val
    def set_business_expenses(self, val): self.business_form_expenses = val
    
    def set_other_income_desc(self, val): self.other_income_form_desc = val
    def set_other_income_amount(self, val): self.other_income_form_amount = val
    def set_other_deduction_desc(self, val): self.other_deduction_form_desc = val
    def set_other_deduction_amount(self, val): self.other_deduction_form_amount = val
    
    def set_dependent_name(self, val): self.dependent_form_name = val
    def set_dependent_relationship(self, val): self.dependent_form_relationship = val
    def set_dependent_age(self, val): self.dependent_form_age = val
    def set_child_care_amount(self, val): self.child_care_form_amount = val
    
    # ===== Form Submit Methods =====
    def submit_rental_form(self):
        """Submit rental property form."""
        try:
            # Monthly rent × 12 = Annual rent income
            monthly_rent = float(self.rental_form_income or 0)
            annual_rent = monthly_rent * 12
            
            # Quarterly property tax × 4 = Annual
            quarterly_tax = float(self.rental_form_tax or 0)
            annual_tax = quarterly_tax * 4
            
            self.add_rental_property(
                address=self.rental_form_address or "Property",
                rent_income=annual_rent,
                mortgage_interest=float(self.rental_form_mortgage or 0),
                property_tax=annual_tax,
                insurance=float(self.rental_form_insurance or 0),
                repairs=float(self.rental_form_repairs or 0),
                depreciation=float(self.rental_form_depreciation or 0),
                other_expenses=float(self.rental_form_other or 0),
                monthly_rent=monthly_rent,  # Store for display
                quarterly_tax=quarterly_tax,  # Store for display
            )
            # Clear form
            self.rental_form_address = ""
            self.rental_form_income = ""
            self.rental_form_mortgage = ""
            self.rental_form_tax = ""
            self.rental_form_insurance = ""
            self.rental_form_repairs = ""
            self.rental_form_depreciation = ""
            self.rental_form_other = ""
            self.show_rental_form = False
            self.success_message = "Rental property added!"
        except ValueError:
            self.error_message = "Invalid numbers in form"
    
    def submit_business_form(self):
        """Submit business income form."""
        try:
            self.add_business(
                name=self.business_form_name or "Business",
                gross_income=float(self.business_form_income or 0),
                expenses=float(self.business_form_expenses or 0),
            )
            self.business_form_name = ""
            self.business_form_income = ""
            self.business_form_expenses = ""
            self.show_business_form = False
            self.success_message = "Business added!"
        except ValueError:
            self.error_message = "Invalid numbers in form"
    
    def submit_other_income_form(self):
        """Submit other income form."""
        try:
            self.add_other_income(
                description=self.other_income_form_desc or "Other Income",
                amount=float(self.other_income_form_amount or 0),
            )
            self.other_income_form_desc = ""
            self.other_income_form_amount = ""
            self.show_other_income_form = False
            self.success_message = "Other income added!"
        except ValueError:
            self.error_message = "Invalid amount"
    
    def submit_other_deduction_form(self):
        """Submit other deduction form."""
        try:
            self.add_other_deduction(
                description=self.other_deduction_form_desc or "Other Deduction",
                amount=float(self.other_deduction_form_amount or 0),
            )
            self.other_deduction_form_desc = ""
            self.other_deduction_form_amount = ""
            self.show_other_deduction_form = False
            self.success_message = "Deduction added!"
        except ValueError:
            self.error_message = "Invalid amount"
    
    def submit_dependent_form(self):
        """Submit dependent form."""
        try:
            age = int(self.dependent_form_age or 0)
            self.add_dependent(
                name=self.dependent_form_name or "Dependent",
                relationship=self.dependent_form_relationship or "Child",
                age=age,
                is_child=(age < 17),
            )
            self.dependent_form_name = ""
            self.dependent_form_relationship = ""
            self.dependent_form_age = ""
            self.show_dependent_form = False
            self.success_message = "Dependent added!"
        except ValueError:
            self.error_message = "Invalid age"
    
    def submit_child_care_expenses(self):
        """Submit child care expenses."""
        try:
            self.child_care_expenses = float(self.child_care_form_amount or 0)
            self.child_care_form_amount = ""
            self._recalculate()
            self.success_message = "Child care expenses updated!"
        except ValueError:
            self.error_message = "Invalid amount"
    
    def remove_file(self, filename: str):
        """Remove an uploaded file and its extracted data."""
        if filename in self.uploaded_files:
            self.uploaded_files.remove(filename)
        if filename in self.selected_files:
            self.selected_files.remove(filename)
        # Remove from parsed_documents
        self.parsed_documents = [
            doc for doc in self.parsed_documents 
            if doc["name"] != filename
        ]
        # Remove extracted W-2 data from this file
        self.w2_list = [
            w for w in self.w2_list 
            if w.get("source_file") != filename
        ]
        # Remove extracted 1099 data from this file
        self.form_1099_list = [
            f for f in self.form_1099_list 
            if f.get("source_file") != filename
        ]
        # Remove extracted 1098 data from this file
        self.form_1098_list = [
            f for f in self.form_1098_list 
            if f.get("source_file") != filename
        ]
        # Remove extracted 5498-SA data from this file
        self.form_5498_list = [
            f for f in self.form_5498_list 
            if f.get("source_file") != filename
        ]
        # Recalculate totals
        self._recalculate()
        
        if not self.uploaded_files:
            self.return_status = "not_started"
    
    def _recalculate(self):
        """Recalculate all tax values following IRS Form 1040 logic."""
        # Get set of included document filenames
        included_files = self.get_included_files()
        
        # Helper to check if item should be included
        def is_included(item):
            source = item.get("source_file")
            # Include if: no source file (manual entry) OR source is in included set
            return source is None or source in included_files
        
        # ===== INCOME (Lines 1-9) =====
        
        # Line 1: Wages (from W-2)
        self.total_wages = sum(w.get("wages", 0) for w in self.w2_list if is_included(w))
        
        # Withholding from all sources
        self.total_withholding = sum(w.get("federal_withheld", 0) for w in self.w2_list if is_included(w))
        self.total_withholding += sum(f.get("federal_withheld", 0) for f in self.form_1099_list if is_included(f))
        self.total_withholding += self.other_withholding  # From 1099-NEC/MISC
        
        # Line 2b: Taxable interest (1099-INT)
        self.total_interest = sum(
            f.get("amount", 0) for f in self.form_1099_list 
            if f.get("form_type") == "1099-INT" and is_included(f)
        )
        
        # Line 3b: Ordinary dividends (1099-DIV)
        self.total_dividends = sum(
            f.get("amount", 0) for f in self.form_1099_list 
            if f.get("form_type") == "1099-DIV" and is_included(f)
        )
        
        # Line 7: Capital gains (1099-B) - simplified, treating all as long-term
        self.total_capital_gains = sum(
            f.get("amount", 0) for f in self.form_1099_list 
            if f.get("form_type") == "1099-B" and is_included(f)
        )
        
        # Other income from 1099 (1099-MISC, 1099-NEC, etc.)
        other_1099_income = sum(
            f.get("amount", 0) for f in self.form_1099_list 
            if f.get("form_type") not in ("1099-INT", "1099-DIV", "1099-B") and is_included(f)
        )
        
        # Schedule E - Rental Property Income (Line 17)
        self.total_rental_income = sum(
            p.get("net_income", 0) for p in self.rental_properties if is_included(p)
        )
        
        # Schedule C - Business Income (Line 3 of Schedule 1)
        self.total_business_income = sum(
            b.get("net_profit", 0) for b in self.business_income if is_included(b)
        )
        
        # Other manual income entries (manual = no source_file, always included)
        manual_other_income = sum(
            i.get("amount", 0) for i in self.other_income if is_included(i)
        )
        
        self.total_other_income = other_1099_income + manual_other_income
        
        # ===== SELF-EMPLOYMENT TAX (Schedule SE) =====
        # SE tax = 15.3% on 92.35% of net self-employment income
        # (12.4% Social Security + 2.9% Medicare)
        # Social Security portion only applies to first $168,600 (2024)
        se_income = self.total_business_income
        if se_income > 0:
            se_taxable = se_income * 0.9235  # 92.35%
            ss_wage_base = 168600  # 2024 limit
            ss_portion = min(se_taxable, ss_wage_base) * 0.124
            medicare_portion = se_taxable * 0.029
            self.self_employment_tax = ss_portion + medicare_portion
            se_deduction = self.self_employment_tax / 2  # Half is deductible
        else:
            self.self_employment_tax = 0.0
            se_deduction = 0.0
        
        # ===== ADJUSTMENTS TO INCOME (Lines 10-22) =====
        
        # HSA deduction (from 5498-SA)
        self.hsa_deduction = sum(
            f.get("contribution", 0) for f in self.form_5498_list if is_included(f)
        )
        
        # Other manual deductions (above-the-line)
        manual_deductions = sum(
            d.get("amount", 0) for d in self.other_deductions if is_included(d)
        )
        
        # Total adjustments to income
        adjustments = self.hsa_deduction + se_deduction + manual_deductions
        
        # Line 9: Total Income
        total_income = (
            self.total_wages + self.total_interest + 
            self.total_dividends + self.total_capital_gains + 
            self.total_rental_income + self.total_business_income +
            self.total_other_income
        )
        
        # Line 11: AGI = Total Income - Adjustments
        self.adjusted_gross_income = max(0, total_income - adjustments)
        
        # ===== DEDUCTIONS (Lines 12-14) =====
        
        # Mortgage interest deduction (from 1098 forms)
        self.mortgage_interest_deduction = sum(
            f.get("mortgage_interest", 0) + f.get("points_paid", 0)
            for f in self.form_1098_list if is_included(f)
        )
        
        # Property taxes (SALT - capped at $10,000)
        property_taxes = sum(f.get("property_taxes", 0) for f in self.form_1098_list if is_included(f))
        salt_deduction = min(property_taxes, 10000)  # SALT cap
        
        # Itemized deductions (Schedule A)
        self.itemized_deductions = self.mortgage_interest_deduction + salt_deduction
        
        # Standard deduction based on filing status
        self.standard_deduction = TAX_CONSTANTS_2024["standard_deduction"].get(
            self.filing_status, 14600
        )
        
        # Use higher of standard or itemized deduction
        self.total_deductions = max(self.standard_deduction, self.itemized_deductions)
        
        # ===== TAXABLE INCOME (Line 15) =====
        self.taxable_income = max(0, self.adjusted_gross_income - self.total_deductions)
        
        # ===== TAX CALCULATION (Line 16) =====
        
        # Separate ordinary income from capital gains for tax calculation
        ordinary_income = self.taxable_income - self.total_capital_gains
        ordinary_income = max(0, ordinary_income)
        
        # Tax on ordinary income (regular brackets)
        brackets = TAX_CONSTANTS_2024["brackets"].get(
            self.filing_status, 
            TAX_CONSTANTS_2024["brackets"]["single"]
        )
        ordinary_tax = self._calculate_tax(ordinary_income, brackets)
        
        # Tax on capital gains (preferential rates) - simplified
        # Note: Capital losses are limited to $3,000/year against ordinary income
        capital_gains_for_tax = self.total_capital_gains
        if capital_gains_for_tax < 0:
            capital_gains_for_tax = max(capital_gains_for_tax, -3000)  # Loss limit
        
        if capital_gains_for_tax > 0:
            cg_brackets = TAX_CONSTANTS_2024["capital_gains_brackets"].get(
                self.filing_status,
                TAX_CONSTANTS_2024["capital_gains_brackets"]["single"]
            )
            self.capital_gains_tax = self._calculate_tax(capital_gains_for_tax, cg_brackets)
        else:
            self.capital_gains_tax = 0.0
        
        # Additional Medicare Tax (0.9% on wages over threshold)
        # Thresholds: MFJ $250k, Single $200k, MFS $125k
        medicare_thresholds = {
            "married_filing_jointly": 250000,
            "qualifying_widow": 250000,
            "single": 200000,
            "head_of_household": 200000,
            "married_filing_separately": 125000,
        }
        medicare_threshold = medicare_thresholds.get(self.filing_status, 200000)
        medicare_base = max(0, self.total_wages - medicare_threshold)
        self.additional_medicare_tax = medicare_base * 0.009
        
        # Net Investment Income Tax (NIIT) - 3.8% on investment income when AGI > threshold
        # Thresholds: MFJ $250k, Single $200k, MFS $125k
        niit_thresholds = {
            "married_filing_jointly": 250000,
            "qualifying_widow": 250000,
            "single": 200000,
            "head_of_household": 200000,
            "married_filing_separately": 125000,
        }
        niit_threshold = niit_thresholds.get(self.filing_status, 200000)
        investment_income = self.total_interest + self.total_dividends + max(0, self.total_capital_gains)
        niit_base = min(investment_income, max(0, self.adjusted_gross_income - niit_threshold))
        self.niit = niit_base * 0.038
        
        # Gross tax before credits
        gross_tax = (ordinary_tax + self.capital_gains_tax + 
                    self.additional_medicare_tax + self.niit + 
                    self.self_employment_tax)
        
        # ===== TAX CREDITS =====
        
        # Child Tax Credit ($2,000 per qualifying child under 17)
        # Phase out: MFJ $400k, others $200k
        ctc_phaseout = 400000 if self.filing_status == "married_filing_jointly" else 200000
        qualifying_children = sum(1 for d in self.dependents if d.get("is_child", False))
        base_ctc = qualifying_children * 2000
        
        # Phase out: reduce by $50 for each $1,000 over threshold
        if self.adjusted_gross_income > ctc_phaseout:
            reduction = ((self.adjusted_gross_income - ctc_phaseout) // 1000) * 50
            self.child_tax_credit = max(0, base_ctc - reduction)
        else:
            self.child_tax_credit = base_ctc
        
        # Credit for Other Dependents ($500 per dependent not qualifying for CTC)
        other_dependents = sum(1 for d in self.dependents if not d.get("is_child", False))
        self.other_dependent_credit = other_dependents * 500
        
        # Child and Dependent Care Credit (20-35% of expenses, max $3,000/1 or $6,000/2+)
        if self.child_care_expenses > 0 and qualifying_children > 0:
            max_expenses = 3000 if qualifying_children == 1 else 6000
            eligible_expenses = min(self.child_care_expenses, max_expenses)
            # Credit rate: 35% if AGI <= $15,000, phases down to 20% at $43,000+
            if self.adjusted_gross_income <= 15000:
                rate = 0.35
            elif self.adjusted_gross_income >= 43000:
                rate = 0.20
            else:
                rate = 0.35 - ((self.adjusted_gross_income - 15000) // 2000) * 0.01
                rate = max(0.20, rate)
            self.child_care_credit = eligible_expenses * rate
        else:
            self.child_care_credit = 0.0
        
        # Total credits (nonrefundable - can't exceed tax)
        self.total_credits = self.child_tax_credit + self.other_dependent_credit + self.child_care_credit
        
        # Total tax after credits
        self.total_tax = max(0, gross_tax - self.total_credits)
        
        # ===== REFUND OR AMOUNT OWED =====
        self.refund_or_owed = self.total_withholding - self.total_tax
        self.is_refund = self.refund_or_owed >= 0
        
        if self.total_wages > 0 or total_income > 0:
            self.return_status = "in_progress"
        
        # Auto-save after recalculation
        self._auto_save()
    
    def _auto_save(self):
        """Auto-save state to disk."""
        try:
            save_state(self)
        except Exception as e:
            print(f"[TaxForge] Auto-save failed: {e}")
    
    def _calculate_tax(self, income: float, brackets: list) -> float:
        """Calculate tax from brackets."""
        tax = 0.0
        remaining = income
        prev = 0.0
        
        for limit, rate in brackets:
            if remaining <= 0:
                break
            bracket_income = min(remaining, limit - prev)
            tax += bracket_income * rate
            remaining -= bracket_income
            prev = limit
        
        return round(tax, 2)
    
    def generate_return(self):
        """Generate tax return."""
        self.processing = True
        self.return_status = "review"
        self.return_generated = True
        self.success_message = "Tax return generated!"
        self.processing = False
    
    def clear_all(self):
        """Clear all data."""
        self.uploaded_files = []
        self.parsed_documents = []
        self.selected_files = []
        self.w2_list = []
        self.form_1098_list = []
        self.form_5498_list = []
        self.rental_properties = []
        self.business_income = []
        self.other_income = []
        self.other_deductions = []
        self.dependents = []
        self.child_care_expenses = 0.0
        self.form_1099_list = []
        self.total_wages = 0.0
        self.total_interest = 0.0
        self.total_dividends = 0.0
        self.total_capital_gains = 0.0
        self.total_rental_income = 0.0
        self.total_business_income = 0.0
        self.total_other_income = 0.0
        self.hsa_deduction = 0.0
        self.self_employment_tax = 0.0
        self.mortgage_interest_deduction = 0.0
        self.adjusted_gross_income = 0.0
        self.itemized_deductions = 0.0
        self.standard_deduction = 0.0
        self.total_deductions = 0.0
        self.taxable_income = 0.0
        self.capital_gains_tax = 0.0
        self.additional_medicare_tax = 0.0
        self.niit = 0.0
        self.total_tax = 0.0
        self.total_withholding = 0.0
        self.other_withholding = 0.0
        self.refund_or_owed = 0.0
        self.is_refund = True
        self.return_status = "not_started"
        self.return_generated = False
        self.error_message = ""
        self.success_message = ""
        # Also clear persisted data
        clear_saved_data()
    
    def load_saved_data(self):
        """Load previously saved data from disk."""
        if load_state(self):
            self.success_message = "Previous session restored!"
        else:
            self.success_message = ""
    
    # ===== Computed Properties =====
    @rx.var
    def formatted_refund(self) -> str:
        """Format refund amount."""
        amount = abs(self.refund_or_owed)
        if self.is_refund:
            return f"+${amount:,.2f}"
        return f"-${amount:,.2f}"
    
    @rx.var
    def has_documents(self) -> bool:
        """Check if documents uploaded."""
        return len(self.parsed_documents) > 0
    
    @rx.var
    def has_income_data(self) -> bool:
        """Check if income data entered."""
        return len(self.w2_list) > 0 or len(self.form_1099_list) > 0
    
    @rx.var
    def can_generate_return(self) -> bool:
        """Check if can generate return."""
        return self.has_income_data
