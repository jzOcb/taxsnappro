"""
Tax calculation modules — Python ports of IRS Direct File XML rules.

Each module registers facts into a FactGraph following the same patterns
as fact_graph.py's build_* functions.
"""

# Federal core module will be imported once available
# from .federal_core import register_all_federal_core

# Investment modules
from .investments import build_all_investment_modules
