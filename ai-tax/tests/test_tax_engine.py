"""
Tests for the tax engine — ensures calculation accuracy.

Tax calculations MUST be deterministic and precisely correct.
These tests use known scenarios from IRS Publication 1436 (ATS test cases)
and manually verified examples.
"""

import pytest
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.tax_engine import SimpleEstimator, STANDARD_DEDUCTION
from core.models import TaxReturn, FilingStatus, Person, W2, Form1099INT, Form1099DIV


class TestSimpleEstimator:
    """Test the quick estimator for sanity checking."""
    
    def setup_method(self):
        self.estimator = SimpleEstimator()
    
    def test_federal_tax_basic_mfj(self):
        """Test federal tax calculation for MFJ with $100K taxable income."""
        tax = SimpleEstimator.estimate_federal_tax(
            Decimal("100000"), FilingStatus.MARRIED_FILING_JOINTLY
        )
        # 10% on first $23,850 = $2,385
        # 12% on $23,850 to $96,950 = $8,772
        # 22% on $96,950 to $100,000 = $671
        expected = Decimal("2385") + Decimal("8772") + Decimal("671")
        assert tax == expected.quantize(Decimal("0.01")), f"Expected {expected}, got {tax}"
    
    def test_federal_tax_high_income_mfj(self):
        """Test federal tax for $500K taxable income MFJ."""
        tax = SimpleEstimator.estimate_federal_tax(
            Decimal("500000"), FilingStatus.MARRIED_FILING_JOINTLY
        )
        # Exact bracket math:
        # 10%: $0-$23,850 → $23,850 × 0.10 = $2,385.00
        # 12%: $23,850-$96,950 → $73,100 × 0.12 = $8,772.00
        # 22%: $96,950-$206,700 → $109,750 × 0.22 = $24,145.00
        # 24%: $206,700-$394,600 → $187,900 × 0.24 = $45,096.00
        # 32%: $394,600-$500,000 → $105,400 × 0.32 = $33,728.00
        expected = (Decimal("2385") + Decimal("8772") + Decimal("24145") + 
                   Decimal("45096") + Decimal("33728"))  # = $114,126
        assert tax == expected.quantize(Decimal("0.01")), f"Expected {expected}, got {tax}"
    
    def test_federal_tax_zero_income(self):
        """Zero income = zero tax."""
        tax = SimpleEstimator.estimate_federal_tax(Decimal("0"))
        assert tax == Decimal("0.00")
    
    def test_ma_tax_basic(self):
        """Test Massachusetts tax calculation."""
        tax = SimpleEstimator.estimate_ma_tax(Decimal("100000"))
        expected = Decimal("100000") * Decimal("0.05")
        assert tax == expected.quantize(Decimal("0.01"))
    
    def test_ma_tax_with_stcg(self):
        """MA short-term capital gains taxed at 8.5%."""
        tax = SimpleEstimator.estimate_ma_tax(
            Decimal("110000"), 
            short_term_gains=Decimal("10000")
        )
        regular = Decimal("100000") * Decimal("0.05")  # $5,000
        stcg = Decimal("10000") * Decimal("0.085")      # $850
        expected = regular + stcg
        assert tax == expected.quantize(Decimal("0.01"))
    
    def test_ma_millionaire_surtax(self):
        """MA 4% surtax on income over $1M."""
        tax = SimpleEstimator.estimate_ma_tax(Decimal("1200000"))
        regular = Decimal("1200000") * Decimal("0.05")  # $60,000
        surtax = Decimal("200000") * Decimal("0.04")     # $8,000
        expected = regular + surtax
        assert tax == expected.quantize(Decimal("0.01"))
    
    def test_quick_estimate_basic(self):
        """Test quick estimate with simple W-2 income."""
        tax_return = TaxReturn(
            tax_year=2025,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        )
        tax_return.w2s = [
            W2(wages=Decimal("275000"), federal_tax_withheld=Decimal("50000")),
            W2(wages=Decimal("275000"), federal_tax_withheld=Decimal("50000")),
        ]
        
        result = self.estimator.quick_estimate(tax_return)
        
        assert result["gross_income"] == Decimal("550000")
        assert result["federal_withholding"] == Decimal("100000")
        assert result["agi"] == Decimal("550000")
        # Taxable = 550K - 30K standard deduction = 520K
        assert result["taxable_income"] == Decimal("520000")
        # Federal tax should be substantial
        assert result["federal_tax"] > Decimal("100000")
    
    def test_standard_deduction_values(self):
        """Verify 2025 standard deduction amounts."""
        assert STANDARD_DEDUCTION[FilingStatus.SINGLE] == Decimal("15000")
        assert STANDARD_DEDUCTION[FilingStatus.MARRIED_FILING_JOINTLY] == Decimal("30000")
        assert STANDARD_DEDUCTION[FilingStatus.HEAD_OF_HOUSEHOLD] == Decimal("22500")


class TestTaxReturnModel:
    """Test the TaxReturn data model."""
    
    def test_total_w2_wages(self):
        tr = TaxReturn()
        tr.w2s = [
            W2(wages=Decimal("100000")),
            W2(wages=Decimal("200000")),
        ]
        assert tr.total_w2_wages == Decimal("300000")
    
    def test_total_withholding(self):
        tr = TaxReturn()
        tr.w2s = [W2(federal_tax_withheld=Decimal("30000"))]
        tr.forms_1099_int = [Form1099INT(federal_tax_withheld=Decimal("500"))]
        tr.forms_1099_div = [Form1099DIV(federal_tax_withheld=Decimal("200"))]
        assert tr.total_federal_withholding == Decimal("30700")
    
    def test_gross_income(self):
        tr = TaxReturn()
        tr.w2s = [W2(wages=Decimal("500000"))]
        tr.forms_1099_int = [Form1099INT(interest_income=Decimal("5000"))]
        tr.forms_1099_div = [Form1099DIV(ordinary_dividends=Decimal("10000"))]
        assert tr.gross_income == Decimal("515000")
    
    def test_empty_return(self):
        tr = TaxReturn()
        assert tr.gross_income == Decimal("0")
        assert tr.total_federal_withholding == Decimal("0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
