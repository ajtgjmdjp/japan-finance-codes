"""Company registry with multi-key lookup indexes."""

from __future__ import annotations

from edinet_mcp import EdinetClient
from edinet_mcp.models import Company


class CompanyRegistry:
    """In-memory registry of Japanese companies with multi-key lookup.

    Build indexes over the EDINET company list to enable O(1) lookup
    by EDINET code, ticker, 5-digit securities code, or corporate number.

    Use the async :meth:`create` factory to construct::

        registry = await CompanyRegistry.create()
        company = registry.by_ticker("7203")
    """

    def __init__(self, companies: list[Company]) -> None:
        self._companies = companies
        self._by_edinet: dict[str, Company] = {}
        self._by_ticker: dict[str, Company] = {}
        self._by_sec_code: dict[str, Company] = {}
        self._by_corporate_number: dict[str, Company] = {}
        self._build_indexes()

    def _build_indexes(self) -> None:
        for c in self._companies:
            self._by_edinet[c.edinet_code] = c
            if c.ticker:
                self._by_ticker[c.ticker] = c
            if c.sec_code:
                self._by_sec_code[c.sec_code] = c
            if c.corporate_number:
                self._by_corporate_number[c.corporate_number] = c

    @classmethod
    async def create(cls, *, api_key: str | None = None) -> CompanyRegistry:
        """Fetch the EDINET company list and build the registry.

        Args:
            api_key: EDINET API key. If ``None``, reads from
                ``EDINET_API_KEY`` environment variable.
        """
        async with EdinetClient(api_key=api_key or "") as client:
            companies = await client.search_companies("")
        return cls(companies)

    @classmethod
    def from_companies(cls, companies: list[Company]) -> CompanyRegistry:
        """Build a registry from a pre-loaded company list."""
        return cls(companies)

    def by_edinet(self, edinet_code: str) -> Company | None:
        """Look up by EDINET code (e.g. ``"E02144"``)."""
        return self._by_edinet.get(edinet_code)

    def by_ticker(self, ticker: str) -> Company | None:
        """Look up by 4-digit ticker (e.g. ``"7203"``)."""
        return self._by_ticker.get(ticker)

    def by_sec_code(self, sec_code: str) -> Company | None:
        """Look up by 5-digit securities code (e.g. ``"72030"``)."""
        return self._by_sec_code.get(sec_code)

    def by_corporate_number(self, corporate_number: str) -> Company | None:
        """Look up by 13-digit corporate number / 法人番号."""
        return self._by_corporate_number.get(corporate_number)

    def search(self, query: str, *, limit: int = 10) -> list[Company]:
        """Search companies by name (substring match).

        Matches against both Japanese and English names.
        Returns up to *limit* results.
        """
        query_lower = query.lower()
        results: list[Company] = []
        for c in self._companies:
            if query_lower in c.name.lower():
                results.append(c)
            elif c.name_en and query_lower in c.name_en.lower():
                results.append(c)
            if len(results) >= limit:
                break
        return results

    def resolve(self, identifier: str) -> Company | None:
        """Auto-detect identifier type and look up.

        Tries EDINET code, ticker, sec_code, corporate number in order.
        """
        if identifier.startswith("E") and len(identifier) == 6:
            return self.by_edinet(identifier)
        if len(identifier) == 4 and identifier.isdigit():
            return self.by_ticker(identifier)
        if len(identifier) == 5 and identifier.isdigit():
            return self.by_sec_code(identifier)
        if len(identifier) == 13 and identifier.isdigit():
            return self.by_corporate_number(identifier)
        # Fallback: try all indexes
        return (
            self._by_edinet.get(identifier)
            or self._by_ticker.get(identifier)
            or self._by_sec_code.get(identifier)
            or self._by_corporate_number.get(identifier)
        )

    @property
    def companies(self) -> list[Company]:
        """All companies in the registry (shallow copy)."""
        return list(self._companies)

    def __len__(self) -> int:
        return len(self._companies)

    def __contains__(self, edinet_code: str) -> bool:
        return edinet_code in self._by_edinet
