"""
Tests for investment modules — Schedule B, D, E, NIIT, Schedule A.
"""

import pytest
from decimal import Decimal
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.fact_graph import FactGraph, FactType
from core.modules.investments import (
    build_schedule_b_module, build_schedule_d_module, build_schedule_e_module,
    build_niit_module, build_schedule_a_module, build_all_investment_modules,
    calculate_ltcg_tax, _calc_niit, CAPITAL_LOSS_LIMIT,
)


class TestLTCGTax:
    """Test long-term capital gains tax calculation."""
    
    def test_zero_bracket_mfj(self):
        """LTCG in 0% bracket for low-income MFJ."""
        tax = calculate_ltcg_tax(Decimal("80000"), Decimal("50000"), is_mfj=True)
        assert tax == Decimal("0.00")
    
    def test_15_percent_bracket(self):
        """LTCG in 15% bracket for typical income."""
        tax = calculate_ltcg_tax(Decimal("300000"), Decimal("50000"), is_mfj=True)
        # All gains should be in 15% bracket
        assert tax == Decimal("7500.00")
    
    def test_mixed_brackets(self):
        """LTCG spanning 15% and 20% brackets."""
        # Taxable income $620K, LTCG $50K
        # Ordinary income = $570K, which is below $600,050 threshold
        # Gains start at $570K: $30,050 at 15%, $19,950 at 20%
        tax = calculate_ltcg_tax(Decimal("620000"), Decimal("50000"), is_mfj=True)
        expected = Decimal("30050") * Decimal("0.15") + Decimal("19950") * Decimal("0.20")
        assert tax == expected.quantize(Decimal("0.01"))


class TestNIIT:
    """Test Net Investment Income Tax."""
    
    def test_below_threshold(self):
        """No NIIT when AGI below threshold."""
        tax = _calc_niit(Decimal("50000"), Decimal("200000"), is_mfj=True)
        assert tax == Decimal("0")
    
    def test_above_threshold_full(self):
        """NIIT on full investment income when AGI far above threshold."""
        # AGI $600K, NII $35K → excess AGI $350K > NII → tax on full $35K
        tax = _calc_niit(Decimal("35000"), Decimal("600000"), is_mfj=True)
        expected = Decimal("35000") * Decimal("0.038")
        assert tax == expected.quantize(Decimal("0.01"))
    
    def test_above_threshold_partial(self):
        """NIIT on partial investment income."""
        # AGI $270K, NII $50K → excess AGI $20K < NII → tax on $20K
        tax = _calc_niit(Decimal("50000"), Decimal("270000"), is_mfj=True)
        expected = Decimal("20000") * Decimal("0.038")
        assert tax == expected.quantize(Decimal("0.01"))


class TestScheduleB:
    """Test Schedule B interest and dividend aggregation."""
    
    def test_interest_aggregation(self):
        graph = FactGraph()
        build_schedule_b_module(graph)
        
        graph.set("/interest/0/amount", Decimal("5000"))
        graph.set("/interest/1/amount", Decimal("3000"))
        
        assert graph.get("/totalInterest") == Decimal("8000")
    
    def test_dividend_aggregation(self):
        graph = FactGraph()
        build_schedule_b_module(graph)
        
        graph.set("/dividends/0/ordinaryDividends", Decimal("10000"))
        graph.set("/dividends/0/qualifiedDividends", Decimal("8000"))
        graph.set("/dividends/1/ordinaryDividends", Decimal("5000"))
        graph.set("/dividends/1/qualifiedDividends", Decimal("4000"))
        
        assert graph.get("/totalOrdinaryDividends") == Decimal("15000")
        assert graph.get("/totalQualifiedDividends") == Decimal("12000")
    
    def test_schedule_b_required(self):
        graph = FactGraph()
        build_schedule_b_module(graph)
        
        graph.set("/interest/0/amount", Decimal("500"))
        assert graph.get("/requiresScheduleB") == False
        
        graph.set("/interest/0/amount", Decimal("2000"))
        assert graph.get("/requiresScheduleB") == True


class TestScheduleD:
    """Test Schedule D capital gains/losses."""
    
    def test_net_capital_gain(self):
        graph = FactGraph()
        build_schedule_b_module(graph)  # needed for capital gain distributions
        build_schedule_d_module(graph)
        
        graph.set("/brokerSummary/shortTermProceeds", Decimal("10000"))
        graph.set("/brokerSummary/shortTermBasis", Decimal("8000"))
        graph.set("/brokerSummary/longTermProceeds", Decimal("50000"))
        graph.set("/brokerSummary/longTermBasis", Decimal("30000"))
        
        assert graph.get("/netShortTermGain") == Decimal("2000")
        assert graph.get("/netLongTermGain") == Decimal("20000")
        assert graph.get("/netCapitalGain") == Decimal("22000")
    
    def test_capital_loss_limitation(self):
        graph = FactGraph()
        build_schedule_b_module(graph)
        build_schedule_d_module(graph)
        
        # Net loss of $10,000
        graph.set("/brokerSummary/shortTermProceeds", Decimal("5000"))
        graph.set("/brokerSummary/shortTermBasis", Decimal("15000"))
        
        # Capital loss deduction capped at -$3,000
        loss_deduction = graph.get("/capitalLossDeduction")
        assert loss_deduction == Decimal("-3000")
        
        # Carryover should be -$7,000
        carryover = graph.get("/newCapitalLossCarryover")
        assert carryover == Decimal("-7000")
    
    def test_capital_loss_carryover_from_prior_year(self):
        graph = FactGraph()
        build_schedule_b_module(graph)
        build_schedule_d_module(graph)
        
        # $5000 gain this year but -$8000 carryover
        graph.set("/brokerSummary/longTermProceeds", Decimal("15000"))
        graph.set("/brokerSummary/longTermBasis", Decimal("10000"))
        graph.set("/capitalLossCarryoverLongTerm", Decimal("-8000"))
        
        assert graph.get("/netLongTermGain") == Decimal("-3000")


class TestScheduleE:
    """Test Schedule E rental property income."""
    
    def test_rental_net_income(self):
        graph = FactGraph()
        build_schedule_e_module(graph)
        
        graph.set("/rental/0/rentsReceived", Decimal("24000"))
        graph.set("/rental/0/expenses/mortgageInterest", Decimal("8000"))
        graph.set("/rental/0/expenses/taxes", Decimal("4000"))
        graph.set("/rental/0/expenses/insurance", Decimal("1500"))
        graph.set("/rental/0/expenses/depreciation", Decimal("10000"))
        
        total_expenses = graph.get("/rental/0/totalExpenses")
        assert total_expenses == Decimal("23500")
        
        net = graph.get("/rental/0/netIncome")
        assert net == Decimal("500")
    
    def test_rental_loss(self):
        graph = FactGraph()
        build_schedule_e_module(graph)
        
        graph.set("/rental/0/rentsReceived", Decimal("18000"))
        graph.set("/rental/0/expenses/mortgageInterest", Decimal("12000"))
        graph.set("/rental/0/expenses/taxes", Decimal("5000"))
        graph.set("/rental/0/expenses/depreciation", Decimal("14545"))
        
        net = graph.get("/rental/0/netIncome")
        assert net == Decimal("-13545")
    
    def test_depreciation_calculation(self):
        graph = FactGraph()
        build_schedule_e_module(graph)
        
        graph.set("/rental/0/purchasePrice", Decimal("500000"))
        graph.set("/rental/0/landValue", Decimal("100000"))
        
        basis = graph.get("/rental/0/depreciableBasis")
        assert basis == Decimal("400000")
        
        annual = graph.get("/rental/0/annualDepreciation")
        assert annual == Decimal("14545.45")
    
    def test_multiple_properties(self):
        graph = FactGraph()
        build_schedule_e_module(graph)
        
        graph.set("/rental/0/rentsReceived", Decimal("24000"))
        graph.set("/rental/0/expenses/mortgageInterest", Decimal("10000"))
        graph.set("/rental/1/rentsReceived", Decimal("30000"))
        graph.set("/rental/1/expenses/mortgageInterest", Decimal("15000"))
        
        total = graph.get("/totalNetRentalIncome")
        assert total == Decimal("29000")  # (24K-10K) + (30K-15K)


class TestScheduleA:
    """Test Schedule A itemized deductions."""
    
    def test_salt_cap(self):
        graph = FactGraph()
        build_schedule_a_module(graph)
        
        graph.set("/itemized/stateIncomeTax", Decimal("30000"))
        graph.set("/itemized/realEstateTax", Decimal("10000"))
        
        # SALT capped at $10,000
        assert graph.get("/itemized/saltDeduction") == Decimal("10000")
    
    def test_medical_deduction_threshold(self):
        graph = FactGraph()
        build_schedule_a_module(graph)
        
        graph.set("/itemized/medicalExpenses", Decimal("50000"))
        graph.set("/itemized/agi_for_medical", Decimal("600000"))
        
        # 7.5% of $600K = $45K threshold
        # $50K - $45K = $5K deduction
        assert graph.get("/itemized/medicalDeduction") == Decimal("5000.00")
    
    def test_itemize_vs_standard(self):
        graph = FactGraph()
        build_schedule_a_module(graph)
        
        graph.set("/standardDeductionAmount", Decimal("30000"))
        graph.set("/itemized/stateIncomeTax", Decimal("10000"))
        graph.set("/itemized/homeMortgageInterest", Decimal("20000"))
        graph.set("/itemized/charityCash", Decimal("5000"))
        
        total = graph.get("/totalItemizedDeductions")
        # SALT $10K (capped) + mortgage $20K + charity $5K = $35K
        assert total == Decimal("35000")
        assert graph.get("/shouldItemize") == True
        assert graph.get("/deductionUsed") == Decimal("35000")
    
    def test_standard_better_than_itemized(self):
        graph = FactGraph()
        build_schedule_a_module(graph)
        
        graph.set("/standardDeductionAmount", Decimal("30000"))
        graph.set("/itemized/stateIncomeTax", Decimal("5000"))
        graph.set("/itemized/homeMortgageInterest", Decimal("8000"))
        
        total = graph.get("/totalItemizedDeductions")
        assert total == Decimal("13000")
        assert graph.get("/shouldItemize") == False
        assert graph.get("/deductionUsed") == Decimal("30000")


class TestAllModulesIntegration:
    """Test all investment modules working together."""
    
    def test_build_all(self):
        graph = FactGraph()
        build_all_investment_modules(graph)
        
        # Should have many facts registered
        assert len(graph._facts) > 100
        
        # Should have all modules
        modules = graph.get_modules()
        assert "scheduleB" in modules
        assert "scheduleD" in modules
        assert "scheduleE" in modules
        assert "niit" in modules
        assert "scheduleA" in modules


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
