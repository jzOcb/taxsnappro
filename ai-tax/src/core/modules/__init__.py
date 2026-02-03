"""
Tax calculation modules — Python ports of IRS Direct File XML rules + custom extensions.

Each module registers facts into a FactGraph following the same patterns
as fact_graph.py's build_* functions.

Modules from Direct File (ported):
- federal_core: Filing status, standard deduction, income, brackets, tax calc
- income_sources: W-2 (enhanced), HSA, Social Security

Custom modules (not in Direct File):
- investments: Schedule A/B/D/E, NIIT, capital gains
"""

from .federal_core import register_all_federal_core
from .income_sources import build_income_sources
from .investments import build_all_investment_modules
