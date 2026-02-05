"""
AI Tax - Application State
"""
import reflex as rx
from typing import List, Dict
from enum import Enum


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
    }
}


class TaxAppState(rx.State):
    """Main application state."""
    
    # ===== UI State =====
    processing: bool = False
    error_message: str = ""
    success_message: str = ""
    
    # ===== User Settings =====
    tax_year: int = 2024
    filing_status: str = "single"
    openai_api_key: str = ""
    
    # ===== Document State =====
    uploaded_files: List[str] = []
    parsed_documents: List[Dict] = []
    
    # ===== Personal Info =====
    first_name: str = ""
    last_name: str = ""
    
    # ===== Tax Data =====
    w2_list: List[Dict] = []
    form_1099_list: List[Dict] = []
    
    # ===== Calculated Values =====
    total_wages: float = 0.0
    total_interest: float = 0.0
    total_dividends: float = 0.0
    total_other_income: float = 0.0
    adjusted_gross_income: float = 0.0
    total_deductions: float = 0.0
    taxable_income: float = 0.0
    total_tax: float = 0.0
    total_withholding: float = 0.0
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
        """Set OpenAI API key."""
        self.openai_api_key = key
    
    async def handle_file_upload(self, files: List[rx.UploadFile]):
        """Handle uploaded tax documents."""
        self.processing = True
        self.error_message = ""
        
        try:
            for file in files:
                file_data = await file.read()
                filename = file.filename
                
                self.uploaded_files.append(filename)
                
                doc_type = self._detect_document_type(filename)
                self.parsed_documents.append({
                    "name": filename,
                    "type": doc_type,
                    "status": "uploaded",
                })
            
            self.return_status = "in_progress"
            self.success_message = f"Uploaded {len(files)} file(s)"
            
        except Exception as e:
            self.error_message = f"Upload failed: {str(e)}"
        finally:
            self.processing = False
    
    def _detect_document_type(self, filename: str) -> str:
        """Detect document type from filename."""
        lower = filename.lower()
        if "w2" in lower or "w-2" in lower:
            return "W-2"
        elif "1099-int" in lower:
            return "1099-INT"
        elif "1099-div" in lower:
            return "1099-DIV"
        elif "1099" in lower:
            return "1099"
        elif "1098" in lower:
            return "1098"
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
    
    def _recalculate(self):
        """Recalculate all tax values."""
        # Sum income
        self.total_wages = sum(w["wages"] for w in self.w2_list)
        self.total_withholding = sum(w["federal_withheld"] for w in self.w2_list)
        
        self.total_interest = sum(
            f["amount"] for f in self.form_1099_list 
            if f["form_type"] == "1099-INT"
        )
        self.total_dividends = sum(
            f["amount"] for f in self.form_1099_list 
            if f["form_type"] == "1099-DIV"
        )
        self.total_other_income = sum(
            f["amount"] for f in self.form_1099_list 
            if f["form_type"] not in ("1099-INT", "1099-DIV")
        )
        
        # AGI
        self.adjusted_gross_income = (
            self.total_wages + self.total_interest + 
            self.total_dividends + self.total_other_income
        )
        
        # Deduction
        self.total_deductions = TAX_CONSTANTS_2024["standard_deduction"].get(
            self.filing_status, 14600
        )
        
        # Taxable income
        self.taxable_income = max(0, self.adjusted_gross_income - self.total_deductions)
        
        # Tax
        brackets = TAX_CONSTANTS_2024["brackets"].get(
            self.filing_status, 
            TAX_CONSTANTS_2024["brackets"]["single"]
        )
        self.total_tax = self._calculate_tax(self.taxable_income, brackets)
        
        # Refund
        self.refund_or_owed = self.total_withholding - self.total_tax
        self.is_refund = self.refund_or_owed >= 0
        
        if self.total_wages > 0:
            self.return_status = "in_progress"
    
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
        self.w2_list = []
        self.form_1099_list = []
        self.total_wages = 0.0
        self.total_interest = 0.0
        self.total_dividends = 0.0
        self.total_other_income = 0.0
        self.adjusted_gross_income = 0.0
        self.total_deductions = 0.0
        self.taxable_income = 0.0
        self.total_tax = 0.0
        self.total_withholding = 0.0
        self.refund_or_owed = 0.0
        self.is_refund = True
        self.return_status = "not_started"
        self.return_generated = False
        self.error_message = ""
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
