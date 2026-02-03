"""
Document Parser — Extract structured data from tax documents.

Architecture:
1. User uploads image/PDF of tax document (W-2, 1099, etc.)
2. OCR layer extracts raw text + layout
3. LLM layer interprets the extracted text into structured fields
4. Validation layer checks for completeness and consistency
5. Human review for low-confidence extractions

This two-stage approach (OCR → LLM) is more reliable than either alone:
- OCR alone: Gets text but can't understand form layout
- LLM alone: Can hallucinate numbers from image
- Combined: OCR provides ground truth text, LLM maps it to fields
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Any

from ..core.models import (
    W2, Form1099INT, Form1099DIV, Form1099B, Form1098,
    DocumentType, Address
)


@dataclass
class ExtractionField:
    """A single extracted field with confidence score."""
    field_name: str
    value: Any
    confidence: float = 0.0  # 0.0 to 1.0
    raw_text: str = ""  # Original OCR text for this field
    needs_review: bool = False


@dataclass
class ExtractionResult:
    """Result of parsing a single document."""
    document_type: DocumentType
    fields: dict[str, ExtractionField] = field(default_factory=dict)
    overall_confidence: float = 0.0
    raw_ocr_text: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    needs_human_review: bool = False
    
    def get_value(self, field_name: str, default=None):
        """Get a field value by name."""
        if field_name in self.fields:
            return self.fields[field_name].value
        return default
    
    def get_decimal(self, field_name: str, default: str = "0") -> Decimal:
        """Get a decimal field value."""
        val = self.get_value(field_name)
        if val is None:
            return Decimal(default)
        try:
            # Clean common OCR artifacts
            cleaned = str(val).replace(",", "").replace("$", "").replace(" ", "")
            return Decimal(cleaned)
        except Exception:
            return Decimal(default)


class OCRProvider(ABC):
    """Abstract OCR provider interface."""
    
    @abstractmethod
    async def extract_text(self, image_bytes: bytes, mime_type: str = "image/png") -> dict:
        """
        Extract text and layout from an image/PDF.
        
        Returns:
            Dict with keys: 'text' (full text), 'blocks' (positioned text blocks),
            'confidence' (overall confidence)
        """
        pass


class LLMExtractor(ABC):
    """Abstract LLM extractor interface."""
    
    @abstractmethod
    async def extract_fields(self, 
                              ocr_text: str, 
                              document_type: DocumentType,
                              image_bytes: Optional[bytes] = None) -> dict:
        """
        Extract structured fields from OCR text using LLM.
        
        Args:
            ocr_text: Raw text from OCR
            document_type: Expected document type
            image_bytes: Optional original image for multimodal models
            
        Returns:
            Dict mapping field names to extracted values
        """
        pass


class DocumentParser:
    """
    Main document parser that orchestrates OCR + LLM extraction.
    
    Usage:
        parser = DocumentParser(ocr_provider, llm_extractor)
        result = await parser.parse(image_bytes, DocumentType.W2)
        w2 = parser.to_w2(result)
    """
    
    # Minimum confidence to accept a field without human review
    CONFIDENCE_THRESHOLD = 0.85
    
    # Fields that are critical and always need high confidence
    CRITICAL_FIELDS = {
        DocumentType.W2: ["employer_ein", "ssn", "wages", "federal_tax_withheld"],
        DocumentType.FORM_1099_INT: ["payer_tin", "interest_income"],
        DocumentType.FORM_1099_DIV: ["payer_tin", "ordinary_dividends", "qualified_dividends"],
    }
    
    def __init__(self, ocr_provider: OCRProvider, llm_extractor: LLMExtractor):
        self.ocr = ocr_provider
        self.llm = llm_extractor
    
    async def parse(self, 
                    image_bytes: bytes,
                    expected_type: Optional[DocumentType] = None,
                    mime_type: str = "image/png") -> ExtractionResult:
        """
        Parse a tax document image/PDF into structured data.
        
        Args:
            image_bytes: Raw image or PDF bytes
            expected_type: If known, the type of document to expect
            mime_type: MIME type of the input
            
        Returns:
            ExtractionResult with extracted fields and confidence scores
        """
        # Step 1: OCR
        ocr_result = await self.ocr.extract_text(image_bytes, mime_type)
        raw_text = ocr_result.get("text", "")
        ocr_confidence = ocr_result.get("confidence", 0.0)
        
        # Step 2: Detect document type if not provided
        if expected_type is None:
            expected_type = self._detect_document_type(raw_text)
        
        # Step 3: LLM extraction
        llm_fields = await self.llm.extract_fields(
            raw_text, expected_type, image_bytes
        )
        
        # Step 4: Build result with confidence scores
        result = ExtractionResult(
            document_type=expected_type,
            raw_ocr_text=raw_text,
            overall_confidence=ocr_confidence,
        )
        
        for field_name, value in llm_fields.items():
            confidence = self._assess_confidence(field_name, value, raw_text, expected_type)
            needs_review = confidence < self.CONFIDENCE_THRESHOLD
            
            # Critical fields always need review if not very high confidence
            if field_name in self.CRITICAL_FIELDS.get(expected_type, []):
                needs_review = confidence < 0.95
            
            result.fields[field_name] = ExtractionField(
                field_name=field_name,
                value=value,
                confidence=confidence,
                raw_text=self._find_raw_text_for_field(field_name, raw_text),
                needs_review=needs_review,
            )
            
            if needs_review:
                result.needs_human_review = True
        
        # Step 5: Cross-validation
        self._cross_validate(result)
        
        return result
    
    def _detect_document_type(self, text: str) -> DocumentType:
        """Detect document type from OCR text."""
        text_lower = text.lower()
        
        if "w-2" in text_lower or "wage and tax statement" in text_lower:
            return DocumentType.W2
        elif "1099-int" in text_lower or "interest income" in text_lower:
            return DocumentType.FORM_1099_INT
        elif "1099-div" in text_lower or "dividends and distributions" in text_lower:
            return DocumentType.FORM_1099_DIV
        elif "1099-b" in text_lower or "proceeds from broker" in text_lower:
            return DocumentType.FORM_1099_B
        elif "1098" in text_lower and "mortgage" in text_lower:
            return DocumentType.FORM_1098
        elif "schedule k-1" in text_lower or "k-1" in text_lower:
            return DocumentType.SCHEDULE_K1
        elif "1099-r" in text_lower:
            return DocumentType.FORM_1099_R
        elif "1099-nec" in text_lower:
            return DocumentType.FORM_1099_NEC
        elif "ssa-1099" in text_lower:
            return DocumentType.SSA_1099
        
        return DocumentType.OTHER
    
    def _assess_confidence(self, field_name: str, value: Any, 
                           raw_text: str, doc_type: DocumentType) -> float:
        """
        Assess confidence of an extracted field.
        
        Factors:
        - Is the value found verbatim in OCR text?
        - Does the value format match expected format?
        - Is the value within reasonable range?
        """
        if value is None or value == "":
            return 0.0
        
        confidence = 0.5  # Base
        
        # Check if value appears in raw OCR text
        str_value = str(value).replace(",", "")
        if str_value in raw_text.replace(",", ""):
            confidence += 0.3
        
        # Format validation
        if self._validate_field_format(field_name, value, doc_type):
            confidence += 0.15
        
        # Range validation
        if self._validate_field_range(field_name, value, doc_type):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _validate_field_format(self, field_name: str, value: Any, doc_type: DocumentType) -> bool:
        """Validate field format (e.g., SSN should be 9 digits, EIN should be 9 digits)."""
        str_val = str(value).replace("-", "").replace(" ", "")
        
        if "ssn" in field_name.lower():
            return len(str_val) == 9 and str_val.isdigit()
        elif "ein" in field_name.lower():
            return len(str_val) == 9 and str_val.isdigit()
        elif any(kw in field_name.lower() for kw in ["wages", "tax", "income", "interest", "dividend"]):
            try:
                Decimal(str_val.replace(",", "").replace("$", ""))
                return True
            except Exception:
                return False
        
        return True  # Default: format OK
    
    def _validate_field_range(self, field_name: str, value: Any, doc_type: DocumentType) -> bool:
        """Validate field value is in reasonable range."""
        try:
            num = Decimal(str(value).replace(",", "").replace("$", ""))
        except Exception:
            return True  # Non-numeric field, skip range check
        
        # Wages should be positive and < $10M (sanity check)
        if "wages" in field_name.lower():
            return Decimal("0") <= num < Decimal("10000000")
        
        # Tax amounts should be non-negative
        if "tax" in field_name.lower():
            return num >= Decimal("0")
        
        return True
    
    def _find_raw_text_for_field(self, field_name: str, raw_text: str) -> str:
        """Find the relevant portion of OCR text for a field (for human review)."""
        # Simplified — in production, use text block positioning from OCR
        return ""
    
    def _cross_validate(self, result: ExtractionResult):
        """Cross-validate extracted fields for consistency."""
        if result.document_type == DocumentType.W2:
            # Medicare wages should be >= regular wages (usually)
            wages = result.get_decimal("wages")
            medicare_wages = result.get_decimal("medicare_wages")
            if medicare_wages > 0 and wages > medicare_wages * Decimal("1.5"):
                result.warnings.append(
                    f"W-2 wages (${wages}) significantly exceed Medicare wages (${medicare_wages}) — verify"
                )
            
            # Federal tax withheld should be reasonable % of wages
            fed_tax = result.get_decimal("federal_tax_withheld")
            if wages > 0:
                effective_rate = fed_tax / wages
                if effective_rate > Decimal("0.50"):
                    result.warnings.append(
                        f"Federal withholding rate ({effective_rate:.0%}) seems too high — verify"
                    )
    
    # ============================================================
    # Converters: ExtractionResult → Data Models
    # ============================================================
    
    @staticmethod
    def to_w2(result: ExtractionResult) -> W2:
        """Convert extraction result to W2 model."""
        return W2(
            employer_name=result.get_value("employer_name", ""),
            employer_ein=result.get_value("employer_ein", ""),
            wages=result.get_decimal("wages"),
            federal_tax_withheld=result.get_decimal("federal_tax_withheld"),
            social_security_wages=result.get_decimal("social_security_wages"),
            social_security_tax=result.get_decimal("social_security_tax"),
            medicare_wages=result.get_decimal("medicare_wages"),
            medicare_tax=result.get_decimal("medicare_tax"),
            state=result.get_value("state", ""),
            state_wages=result.get_decimal("state_wages"),
            state_tax_withheld=result.get_decimal("state_tax_withheld"),
            retirement_plan=result.get_value("retirement_plan", False),
        )
    
    @staticmethod
    def to_1099_int(result: ExtractionResult) -> Form1099INT:
        """Convert extraction result to Form1099INT model."""
        return Form1099INT(
            payer_name=result.get_value("payer_name", ""),
            interest_income=result.get_decimal("interest_income"),
            early_withdrawal_penalty=result.get_decimal("early_withdrawal_penalty"),
            federal_tax_withheld=result.get_decimal("federal_tax_withheld"),
            tax_exempt_interest=result.get_decimal("tax_exempt_interest"),
        )
    
    @staticmethod
    def to_1099_div(result: ExtractionResult) -> Form1099DIV:
        """Convert extraction result to Form1099DIV model."""
        return Form1099DIV(
            payer_name=result.get_value("payer_name", ""),
            ordinary_dividends=result.get_decimal("ordinary_dividends"),
            qualified_dividends=result.get_decimal("qualified_dividends"),
            total_capital_gain=result.get_decimal("total_capital_gain"),
            federal_tax_withheld=result.get_decimal("federal_tax_withheld"),
            foreign_tax_paid=result.get_decimal("foreign_tax_paid"),
        )
