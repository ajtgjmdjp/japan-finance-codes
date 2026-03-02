"""japan-finance-codes: Unified company ID registry for Japanese financial data.

Quick start (offline, no API key needed)::

    from japan_finance_codes import CompanyRegistry

    registry = CompanyRegistry.create()
    company = registry.by_ticker("7203")      # Toyota
    company = registry.by_edinet("E02144")    # Same company
    results = registry.search("トヨタ")        # Fuzzy name search
"""

from japan_finance_codes._registry import CompanyLike, CompanyRegistry

__all__ = ["CompanyLike", "CompanyRegistry"]
__version__ = "0.2.0"
