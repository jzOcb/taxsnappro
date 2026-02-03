"""
Tests for the Fact Graph — the core knowledge graph for tax data.
"""

import pytest
from decimal import Decimal

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.fact_graph import (
    FactGraph, Fact, FactType, FactStatus,
    build_standard_graph, get_next_questions
)


class TestFactGraph:
    
    def test_register_and_get_writable(self):
        graph = FactGraph()
        graph.register_writable("/test", "Test Fact", FactType.STRING)
        graph.set("/test", "hello")
        assert graph.get("/test") == "hello"
    
    def test_derived_fact(self):
        graph = FactGraph()
        graph.register_writable("/a", "A", FactType.DECIMAL)
        graph.register_writable("/b", "B", FactType.DECIMAL)
        graph.register_derived(
            "/sum", "Sum", FactType.DECIMAL,
            dependencies=["/a", "/b"],
            derive_fn=lambda deps: (deps["/a"] or Decimal("0")) + (deps["/b"] or Decimal("0"))
        )
        
        graph.set("/a", Decimal("100"))
        graph.set("/b", Decimal("200"))
        assert graph.get("/sum") == Decimal("300")
    
    def test_cannot_set_derived(self):
        graph = FactGraph()
        graph.register_derived("/x", "X", derive_fn=lambda d: 0)
        with pytest.raises(ValueError):
            graph.set("/x", 42)
    
    def test_missing_facts(self):
        graph = FactGraph()
        graph.register_writable("/name", "Name", FactType.STRING, module="filers")
        graph.register_writable("/ssn", "SSN", FactType.STRING, module="filers")
        
        missing = graph.get_missing_facts()
        assert len(missing) == 2
        
        graph.set("/name", "Jason")
        missing = graph.get_missing_facts()
        assert len(missing) == 1
        assert missing[0].path == "/ssn"
    
    def test_completion_percentage(self):
        graph = FactGraph()
        graph.register_writable("/a", "A", module="test")
        graph.register_writable("/b", "B", module="test")
        graph.register_writable("/c", "C", module="test")
        
        assert graph.completion_percentage("test") == 0.0
        
        graph.set("/a", "x")
        assert abs(graph.completion_percentage("test") - 33.33) < 1
        
        graph.set("/b", "y")
        graph.set("/c", "z")
        assert graph.completion_percentage("test") == 100.0
    
    def test_ssn_validation(self):
        graph = FactGraph()
        graph.register_writable("/ssn", "SSN", FactType.STRING,
                               validators=[lambda v: "Bad SSN" if v and len(str(v).replace("-","")) != 9 else None])
        
        graph.set("/ssn", "123")
        assert graph.get_status("/ssn") == FactStatus.ERROR
        
        graph.set("/ssn", "123-45-6789")
        assert graph.get_status("/ssn") == FactStatus.COMPLETE
    
    def test_mef_export(self):
        graph = FactGraph()
        graph.register_writable("/wages", "Wages", FactType.DECIMAL, export_mef=True)
        graph.register_writable("/name", "Name", FactType.STRING, export_mef=False)
        
        graph.set("/wages", Decimal("50000"))
        graph.set("/name", "Jason")
        
        mef = graph.get_mef_facts()
        assert "/wages" in mef
        assert "/name" not in mef
    
    def test_serialization(self):
        graph = FactGraph()
        graph.register_writable("/a", "A", FactType.STRING)
        graph.register_writable("/b", "B", FactType.DECIMAL)
        
        graph.set("/a", "hello")
        graph.set("/b", Decimal("100"))
        
        data = graph.to_dict()
        
        # Create fresh graph and restore
        graph2 = FactGraph()
        graph2.register_writable("/a", "A", FactType.STRING)
        graph2.register_writable("/b", "B", FactType.DECIMAL)
        graph2.load_dict(data)
        
        assert graph2.get("/a") == "hello"
        assert graph2.get("/b") == Decimal("100")
    
    def test_chained_derivations(self):
        """Test that derived facts can depend on other derived facts."""
        graph = FactGraph()
        graph.register_writable("/x", "X", FactType.DECIMAL)
        graph.register_derived(
            "/double", "Double", FactType.DECIMAL,
            dependencies=["/x"],
            derive_fn=lambda d: (d["/x"] or Decimal("0")) * 2
        )
        graph.register_derived(
            "/quadruple", "Quadruple", FactType.DECIMAL,
            dependencies=["/double"],
            derive_fn=lambda d: (d["/double"] or Decimal("0")) * 2
        )
        
        graph.set("/x", Decimal("10"))
        assert graph.get("/double") == Decimal("20")
        assert graph.get("/quadruple") == Decimal("40")


class TestStandardGraph:
    
    def test_build_standard_graph(self):
        graph = build_standard_graph()
        assert len(graph._facts) > 20
        assert "filers" in graph.get_modules()
        assert "filingStatus" in graph.get_modules()
    
    def test_standard_graph_flow(self):
        """Simulate a basic tax return through the fact graph."""
        graph = build_standard_graph()
        
        # Set filing status
        graph.set("/filingStatus", "married_filing_jointly")
        assert graph.get("/isFilingStatusMFJ") == True
        assert graph.get("/standardDeduction") == Decimal("30000")
        
        # Set W-2 income
        graph.set("/filers/primary/w2s/0/wages", Decimal("275000"))
        graph.set("/filers/primary/w2s/0/federalTaxWithheld", Decimal("50000"))
        
        # Check derived values
        assert graph.get("/totalWages") == Decimal("275000")
        assert graph.get("/totalFederalTaxWithheld") == Decimal("50000")
    
    def test_get_next_questions(self):
        graph = build_standard_graph()
        questions = get_next_questions(graph, max_questions=5)
        assert len(questions) > 0
        # First questions should be from filers module
        assert questions[0]["module"] == "filers"
    
    def test_module_completion(self):
        graph = build_standard_graph()
        completion = graph.module_completion()
        # Modules with writable facts should start at 0%
        assert completion["filers"] == 0.0
        assert completion["formW2s"] == 0.0
        # taxCalculations has only derived facts → 100% (no writable to fill)
        assert completion["taxCalculations"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
