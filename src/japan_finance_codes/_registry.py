"""Company registry with multi-key lookup indexes."""

from __future__ import annotations

import unicodedata

from edinet_mcp import EdinetClient
from edinet_mcp.models import Company

# Match-quality scores (higher = better match)
_SCORE_EXACT = 3
_SCORE_PREFIX = 2
_SCORE_CONTAINS = 1


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

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for fuzzy matching.

        Applies NFKC normalization (full-width → half-width, etc.)
        and lowercases for case-insensitive comparison.
        """
        return unicodedata.normalize("NFKC", text).lower()

    def _score_match(self, name: str, tokens: list[str]) -> int:
        """Score how well *name* matches the search tokens.

        Returns 0 for no match. Higher is better.
        """
        normalized = self._normalize(name)
        # All tokens must appear in the name
        for token in tokens:
            if token not in normalized:
                return 0

        # Single-token scoring: exact > prefix > contains
        if len(tokens) == 1:
            token = tokens[0]
            if normalized == token:
                return _SCORE_EXACT
            if normalized.startswith(token):
                return _SCORE_PREFIX
            return _SCORE_CONTAINS

        # Multi-token: all matched → contains-level
        return _SCORE_CONTAINS

    def search(self, query: str, *, limit: int = 10) -> list[Company]:
        """Search companies by name with ranked fuzzy matching.

        Features:
        - NFKC normalization (full-width/half-width unification)
        - Score-based ranking: exact > prefix > contains
        - Multi-token AND search (space-separated)
        - Matches against both Japanese and English names.

        Returns up to *limit* results, best matches first.
        """
        normalized_query = self._normalize(query)
        tokens = normalized_query.split()
        if not tokens:
            return []

        scored: list[tuple[int, Company]] = []
        for c in self._companies:
            best = self._score_match(c.name, tokens)
            if c.name_en:
                best = max(best, self._score_match(c.name_en, tokens))
            if best > 0:
                scored.append((best, c))

        # Sort by score descending, then by name for stability
        scored.sort(key=lambda pair: (-pair[0], pair[1].name))
        return [c for _, c in scored[:limit]]

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
