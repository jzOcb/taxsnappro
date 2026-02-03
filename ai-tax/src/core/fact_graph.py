"""
Fact Graph — Python implementation inspired by IRS Direct File's Scala Fact Graph.

The IRS Direct File uses a declarative XML-based knowledge graph (Fact Graph) to reason
about incomplete tax return data. This module implements a similar concept in Python.

Key concepts from Direct File:
- **Writable Facts**: User-entered data (name, income amounts, etc.)
- **Derived Facts**: Calculated values based on other facts (AGI, tax owed, etc.)
- **Modules**: Logical groupings (W-2s, HSA, EITC, filing status, etc.)
- **Dependencies**: A fact can depend on facts in the same or other modules
- **Completeness**: The graph tracks which facts are complete/incomplete

Our Python version simplifies the Scala implementation while preserving the core
declarative approach. Instead of XML definitions + Scala runtime, we use Python
dataclasses + a simple evaluation engine.

Reference: github.com/IRS-Public/direct-file/direct-file/fact-graph-scala/
Reference: direct-file/df-client/df-client-app/src/fact-dictionary/generate-src/xml-src/
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Optional, Union
import logging

logger = logging.getLogger(__name__)


class FactType(Enum):
    """Types of facts, matching Direct File's type system."""
    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DECIMAL = "decimal"
    ENUM = "enum"
    DATE = "date"
    COLLECTION = "collection"
    ADDRESS = "address"
    EMAIL = "email"


class FactStatus(Enum):
    """Status of a fact in the graph."""
    EMPTY = "empty"          # No value set yet
    COMPLETE = "complete"    # Value is set and valid
    INCOMPLETE = "incomplete"  # Value is partially set (e.g., collection needs more items)
    ERROR = "error"          # Value fails validation
    DERIVED = "derived"      # Value is calculated from dependencies


@dataclass
class Fact:
    """
    A single fact in the tax knowledge graph.
    
    Mirrors Direct File's XML Fact definition:
    <Fact path="/wages">
      <Name>Total Wages</Name>
      <Writable><Decimal /></Writable>  -- OR --
      <Derived><Add>...</Add></Derived>
    </Fact>
    """
    path: str                           # e.g., "/agi", "/filers/#id/firstName"
    name: str = ""                      # Human-readable name
    description: str = ""               # Longer description
    fact_type: FactType = FactType.STRING
    module: str = ""                    # Which module this belongs to
    
    # Is this user-entered (writable) or calculated (derived)?
    is_writable: bool = True
    
    # Current value
    value: Any = None
    status: FactStatus = FactStatus.EMPTY
    
    # For derived facts: function that computes value from dependencies
    derive_fn: Optional[Callable] = None
    
    # Dependencies (paths of facts this depends on)
    dependencies: list[str] = field(default_factory=list)
    
    # Export flags (from Direct File)
    export_mef: bool = False            # Include in MeF XML output
    export_downstream: bool = False      # Available to other modules
    
    # Validation
    validators: list[Callable] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    
    def is_complete(self) -> bool:
        return self.status == FactStatus.COMPLETE or self.status == FactStatus.DERIVED
    
    def set_value(self, value: Any):
        """Set a writable fact's value."""
        if not self.is_writable:
            raise ValueError(f"Cannot set derived fact: {self.path}")
        self.value = value
        self.validation_errors = []
        for validator in self.validators:
            try:
                error = validator(value)
                if error:
                    self.validation_errors.append(error)
            except Exception as e:
                self.validation_errors.append(str(e))
        
        if self.validation_errors:
            self.status = FactStatus.ERROR
        elif value is not None:
            self.status = FactStatus.COMPLETE
        else:
            self.status = FactStatus.EMPTY


class FactGraph:
    """
    The tax knowledge graph — a directed acyclic graph of facts.
    
    Writable facts are set by the user (via AI conversation or document parsing).
    Derived facts are automatically calculated when their dependencies change.
    
    Usage:
        graph = FactGraph()
        
        # Register modules
        graph.register_module(w2_module)
        graph.register_module(income_module)
        
        # Set writable facts
        graph.set("/filers/#primary/w2s/#0/wages", Decimal("275000"))
        graph.set("/filers/#primary/w2s/#0/federalTaxWithheld", Decimal("50000"))
        
        # Derived facts auto-calculate
        agi = graph.get("/agi")
        
        # Check what's still needed
        missing = graph.get_missing_facts()
    """
    
    def __init__(self):
        self._facts: dict[str, Fact] = {}
        self._modules: dict[str, list[str]] = {}  # module_name -> [fact_paths]
        self._evaluation_order: list[str] = []     # Topologically sorted
        self._dirty: bool = True                    # Needs re-evaluation
    
    def register_fact(self, fact: Fact):
        """Register a fact in the graph."""
        self._facts[fact.path] = fact
        
        # Track module membership
        if fact.module:
            if fact.module not in self._modules:
                self._modules[fact.module] = []
            self._modules[fact.module].append(fact.path)
        
        self._dirty = True
    
    def register_writable(self, path: str, name: str = "", fact_type: FactType = FactType.STRING,
                          module: str = "", description: str = "", export_mef: bool = False,
                          validators: list[Callable] = None):
        """Convenience: register a writable (user-entered) fact."""
        self.register_fact(Fact(
            path=path, name=name, description=description,
            fact_type=fact_type, module=module, is_writable=True,
            export_mef=export_mef, validators=validators or [],
        ))
    
    def register_derived(self, path: str, name: str = "", fact_type: FactType = FactType.DECIMAL,
                         module: str = "", description: str = "", 
                         dependencies: list[str] = None,
                         derive_fn: Callable = None,
                         export_mef: bool = False, export_downstream: bool = False):
        """Convenience: register a derived (calculated) fact."""
        self.register_fact(Fact(
            path=path, name=name, description=description,
            fact_type=fact_type, module=module, is_writable=False,
            derive_fn=derive_fn, dependencies=dependencies or [],
            export_mef=export_mef, export_downstream=export_downstream,
        ))
    
    def set(self, path: str, value: Any):
        """Set a writable fact value, triggering re-evaluation of dependents."""
        if path not in self._facts:
            raise KeyError(f"Unknown fact: {path}")
        
        fact = self._facts[path]
        fact.set_value(value)
        self._dirty = True
        
        # Re-evaluate derived facts that depend on this one
        self._evaluate_dependents(path)
    
    def get(self, path: str) -> Any:
        """Get a fact's current value."""
        if path not in self._facts:
            return None
        
        if self._dirty:
            self._evaluate_all()
        
        return self._facts[path].value
    
    def get_fact(self, path: str) -> Optional[Fact]:
        """Get the full Fact object."""
        return self._facts.get(path)
    
    def get_status(self, path: str) -> FactStatus:
        """Get a fact's current status."""
        if path not in self._facts:
            return FactStatus.EMPTY
        return self._facts[path].status
    
    # ============================================================
    # Completeness Tracking (key for AI interview flow)
    # ============================================================
    
    def get_missing_facts(self, module: str = None) -> list[Fact]:
        """
        Get all writable facts that haven't been filled in yet.
        This drives the AI conversation — the LLM asks about missing facts.
        
        Args:
            module: If specified, only check facts in this module
        """
        missing = []
        paths = self._modules.get(module, self._facts.keys()) if module else self._facts.keys()
        
        for path in paths:
            fact = self._facts.get(path)
            if fact and fact.is_writable and fact.status == FactStatus.EMPTY:
                missing.append(fact)
        
        return missing
    
    def get_complete_facts(self, module: str = None) -> list[Fact]:
        """Get all facts that have values."""
        complete = []
        paths = self._modules.get(module, self._facts.keys()) if module else self._facts.keys()
        
        for path in paths:
            fact = self._facts.get(path)
            if fact and fact.is_complete():
                complete.append(fact)
        
        return complete
    
    def get_error_facts(self) -> list[Fact]:
        """Get all facts with validation errors."""
        return [f for f in self._facts.values() if f.status == FactStatus.ERROR]
    
    def completion_percentage(self, module: str = None) -> float:
        """What percentage of writable facts are complete?"""
        writable = [f for f in self._facts.values() 
                    if f.is_writable and (module is None or f.module == module)]
        if not writable:
            return 100.0
        complete = [f for f in writable if f.is_complete()]
        return len(complete) / len(writable) * 100
    
    def get_modules(self) -> list[str]:
        """Get list of registered modules."""
        return list(self._modules.keys())
    
    def module_completion(self) -> dict[str, float]:
        """Get completion percentage for each module."""
        return {mod: self.completion_percentage(mod) for mod in self._modules}
    
    # ============================================================
    # MeF Export (for XML generation)
    # ============================================================
    
    def get_mef_facts(self) -> dict[str, Any]:
        """Get all facts marked for MeF export, with their values."""
        if self._dirty:
            self._evaluate_all()
        
        return {
            path: fact.value 
            for path, fact in self._facts.items() 
            if fact.export_mef and fact.is_complete()
        }
    
    # ============================================================
    # Evaluation Engine
    # ============================================================
    
    def _evaluate_all(self):
        """Re-evaluate all derived facts in dependency order."""
        if not self._dirty:
            return
        
        # Topological sort of derived facts
        order = self._topological_sort()
        
        for path in order:
            fact = self._facts[path]
            if not fact.is_writable and fact.derive_fn:
                self._evaluate_fact(fact)
        
        self._dirty = False
    
    def _evaluate_fact(self, fact: Fact):
        """Evaluate a single derived fact."""
        if fact.is_writable:
            return
        
        if not fact.derive_fn:
            return
        
        # Check if all dependencies are complete
        dep_values = {}
        all_deps_ready = True
        
        for dep_path in fact.dependencies:
            dep = self._facts.get(dep_path)
            if dep is None:
                logger.warning(f"Missing dependency {dep_path} for fact {fact.path}")
                all_deps_ready = False
                break
            if not dep.is_complete():
                all_deps_ready = False
                break
            dep_values[dep_path] = dep.value
        
        if all_deps_ready:
            try:
                fact.value = fact.derive_fn(dep_values)
                fact.status = FactStatus.DERIVED
            except Exception as e:
                logger.error(f"Error evaluating {fact.path}: {e}")
                fact.value = None
                fact.status = FactStatus.ERROR
                fact.validation_errors = [str(e)]
        else:
            fact.value = None
            fact.status = FactStatus.INCOMPLETE
    
    def _evaluate_dependents(self, changed_path: str):
        """Re-evaluate facts that depend on the changed fact."""
        for path, fact in self._facts.items():
            if changed_path in fact.dependencies:
                self._evaluate_fact(fact)
    
    def _topological_sort(self) -> list[str]:
        """Sort facts in dependency order (leaves first)."""
        visited = set()
        order = []
        
        def visit(path):
            if path in visited:
                return
            visited.add(path)
            fact = self._facts.get(path)
            if fact:
                for dep in fact.dependencies:
                    visit(dep)
            order.append(path)
        
        for path in self._facts:
            visit(path)
        
        return order
    
    # ============================================================
    # Serialization (for persistence)
    # ============================================================
    
    def to_dict(self) -> dict:
        """Serialize all writable fact values (for saving tax return state)."""
        return {
            path: {
                "value": fact.value,
                "status": fact.status.value,
            }
            for path, fact in self._facts.items()
            if fact.is_writable and fact.value is not None
        }
    
    def load_dict(self, data: dict):
        """Restore writable fact values from serialized data."""
        for path, info in data.items():
            if path in self._facts and self._facts[path].is_writable:
                self._facts[path].set_value(info.get("value"))
        self._dirty = True
        self._evaluate_all()
    
    def __repr__(self):
        total = len(self._facts)
        writable = sum(1 for f in self._facts.values() if f.is_writable)
        derived = total - writable
        complete = sum(1 for f in self._facts.values() if f.is_complete())
        return f"FactGraph({total} facts: {writable} writable, {derived} derived, {complete} complete)"


# ============================================================
# Module Builders — Create fact graph modules matching Direct File
# ============================================================

def build_filer_module(graph: FactGraph):
    """Register filer identity facts (name, SSN, DOB, etc.)."""
    module = "filers"
    
    graph.register_writable("/filers/primary/firstName", "First Name", FactType.STRING, module)
    graph.register_writable("/filers/primary/middleInitial", "Middle Initial", FactType.STRING, module)
    graph.register_writable("/filers/primary/lastName", "Last Name", FactType.STRING, module)
    graph.register_writable("/filers/primary/ssn", "SSN", FactType.STRING, module,
                           validators=[lambda v: "SSN must be 9 digits" if v and len(str(v).replace("-","")) != 9 else None])
    graph.register_writable("/filers/primary/dateOfBirth", "Date of Birth", FactType.DATE, module)
    graph.register_writable("/filers/primary/occupation", "Occupation", FactType.STRING, module)
    graph.register_writable("/filers/primary/isUsCitizenFullYear", "US Citizen Full Year", FactType.BOOLEAN, module)
    graph.register_writable("/filers/primary/isBlind", "Is Blind", FactType.BOOLEAN, module)
    graph.register_writable("/filers/primary/is65OrOlder", "Is 65 or Older", FactType.BOOLEAN, module)


def build_filing_status_module(graph: FactGraph):
    """Register filing status facts."""
    module = "filingStatus"
    
    graph.register_writable("/filingStatus", "Filing Status", FactType.ENUM, module,
                           export_mef=True)
    
    graph.register_derived("/isFilingStatusMFJ", "Is MFJ", FactType.BOOLEAN, module,
                          dependencies=["/filingStatus"],
                          derive_fn=lambda deps: deps["/filingStatus"] == "married_filing_jointly",
                          export_downstream=True)
    
    graph.register_derived("/isFilingStatusSingle", "Is Single", FactType.BOOLEAN, module,
                          dependencies=["/filingStatus"],
                          derive_fn=lambda deps: deps["/filingStatus"] == "single")


def build_w2_module(graph: FactGraph, w2_index: int = 0, filer: str = "primary"):
    """Register W-2 facts for a single W-2."""
    module = "formW2s"
    prefix = f"/filers/{filer}/w2s/{w2_index}"
    
    graph.register_writable(f"{prefix}/employerName", "Employer Name", FactType.STRING, module)
    graph.register_writable(f"{prefix}/employerEin", "Employer EIN", FactType.STRING, module, export_mef=True)
    graph.register_writable(f"{prefix}/wages", "Wages (Box 1)", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/federalTaxWithheld", "Federal Tax Withheld (Box 2)", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/socialSecurityWages", "SS Wages (Box 3)", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/socialSecurityTax", "SS Tax (Box 4)", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/medicareWages", "Medicare Wages (Box 5)", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/medicareTax", "Medicare Tax (Box 6)", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/stateWages", "State Wages (Box 16)", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/stateTaxWithheld", "State Tax Withheld (Box 17)", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable(f"{prefix}/state", "State", FactType.STRING, module)
    graph.register_writable(f"{prefix}/retirementPlan", "Has Retirement Plan (Box 13)", FactType.BOOLEAN, module)


def build_income_module(graph: FactGraph):
    """Register income aggregation facts (derived)."""
    module = "income"
    
    # Total W-2 wages — sums across all W-2s
    # In a real implementation, this would dynamically handle any number of W-2s
    graph.register_derived(
        "/totalWages", "Total W-2 Wages", FactType.DECIMAL, module,
        dependencies=["/filers/primary/w2s/0/wages"],
        derive_fn=lambda deps: sum(v for v in deps.values() if v is not None),
        export_mef=True,
    )
    
    graph.register_writable("/totalInterestIncome", "Total Interest Income", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable("/totalOrdinaryDividends", "Total Ordinary Dividends", FactType.DECIMAL, module, export_mef=True)
    graph.register_writable("/totalQualifiedDividends", "Total Qualified Dividends", FactType.DECIMAL, module, export_mef=True)
    
    # Gross income
    graph.register_derived(
        "/grossIncome", "Gross Income", FactType.DECIMAL, module,
        dependencies=["/totalWages", "/totalInterestIncome", "/totalOrdinaryDividends"],
        derive_fn=lambda deps: sum((v or Decimal("0")) for v in deps.values()),
        export_mef=True,
    )


def build_tax_calculation_module(graph: FactGraph):
    """Register tax calculation facts — the core 1040 math."""
    module = "taxCalculations"
    
    # Standard deduction (simplified — Direct File has much more complex logic)
    graph.register_derived(
        "/standardDeduction", "Standard Deduction", FactType.DECIMAL, module,
        dependencies=["/isFilingStatusMFJ"],
        derive_fn=lambda deps: Decimal("30000") if deps.get("/isFilingStatusMFJ") else Decimal("15000"),
        export_mef=True,
    )
    
    # AGI
    graph.register_derived(
        "/agi", "Adjusted Gross Income", FactType.DECIMAL, module,
        dependencies=["/grossIncome"],
        derive_fn=lambda deps: deps.get("/grossIncome", Decimal("0")),
        export_mef=True, export_downstream=True,
    )
    
    # Taxable income
    graph.register_derived(
        "/taxableIncome", "Taxable Income", FactType.DECIMAL, module,
        dependencies=["/agi", "/standardDeduction"],
        derive_fn=lambda deps: max(
            (deps.get("/agi") or Decimal("0")) - (deps.get("/standardDeduction") or Decimal("0")),
            Decimal("0")
        ),
        export_mef=True,
    )
    
    # Total federal tax withheld
    graph.register_derived(
        "/totalFederalTaxWithheld", "Total Federal Tax Withheld", FactType.DECIMAL, module,
        dependencies=["/filers/primary/w2s/0/federalTaxWithheld"],
        derive_fn=lambda deps: sum(v for v in deps.values() if v is not None),
        export_mef=True,
    )


def build_standard_graph() -> FactGraph:
    """
    Build a standard fact graph with all modules.
    This is the default graph for a simple tax return.
    """
    graph = FactGraph()
    
    build_filer_module(graph)
    build_filing_status_module(graph)
    build_w2_module(graph, w2_index=0, filer="primary")
    build_income_module(graph)
    build_tax_calculation_module(graph)
    
    return graph


# ============================================================
# AI Integration Point
# ============================================================

def get_next_questions(graph: FactGraph, max_questions: int = 3) -> list[dict]:
    """
    Determine what to ask the user next based on the current graph state.
    
    This is the key integration point between the Fact Graph and the AI conversation.
    The AI LLM receives this list and formulates natural language questions.
    
    Returns list of dicts: [{"path": ..., "name": ..., "type": ..., "module": ...}]
    """
    missing = graph.get_missing_facts()
    
    # Priority order: personal info → filing status → income → deductions → credits
    module_priority = [
        "filers", "filingStatus", "formW2s", "income", 
        "interest", "hsa", "taxCalculations"
    ]
    
    # Sort missing facts by module priority
    def priority_key(fact):
        try:
            return module_priority.index(fact.module)
        except ValueError:
            return 999
    
    missing.sort(key=priority_key)
    
    return [
        {
            "path": f.path,
            "name": f.name,
            "type": f.fact_type.value,
            "module": f.module,
            "description": f.description,
        }
        for f in missing[:max_questions]
    ]
