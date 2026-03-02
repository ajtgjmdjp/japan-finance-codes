"""Company registry with multi-key lookup indexes."""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

from japan_finance_codes._snapshot import load_snapshot


@runtime_checkable
class CompanyLike(Protocol):
    """Structural type for company records.

    Both ``_CompanyRecord`` (from snapshot) and ``edinet_mcp.models.Company``
    (from live API) satisfy this protocol.
    """

    edinet_code: str
    name: str
    name_en: str | None
    ticker: str | None
    sec_code: str | None
    corporate_number: str | None
    industry: str | None
    accounting_standard: str | None
    is_listed: bool


# Match-quality scores (higher = better match)
_SCORE_EXACT = 3
_SCORE_PREFIX = 2
_SCORE_CONTAINS = 1


class _CompanyRecord:
    """Lightweight company record from snapshot data.

    Used as the default data model when edinet-mcp is not installed.
    Provides the same attribute interface as edinet_mcp.models.Company.
    """

    __slots__ = (
        "accounting_standard",
        "corporate_number",
        "edinet_code",
        "industry",
        "is_listed",
        "name",
        "name_en",
        "sec_code",
        "ticker",
    )

    def __init__(self, **kwargs: Any) -> None:
        self.edinet_code: str = kwargs.get("edinet_code", "")
        self.name: str = kwargs.get("name", "")
        self.name_en: str | None = kwargs.get("name_en")
        self.ticker: str | None = kwargs.get("ticker")
        self.sec_code: str | None = kwargs.get("sec_code")
        self.corporate_number: str | None = kwargs.get("corporate_number")
        self.industry: str | None = kwargs.get("industry")
        self.accounting_standard: str | None = kwargs.get("accounting_standard")
        self.is_listed: bool = kwargs.get("is_listed", False)


class CompanyRegistry:
    """In-memory registry of Japanese companies with multi-key lookup.

    Build indexes over the company list to enable O(1) lookup
    by EDINET code, ticker, 5-digit securities code, or corporate number.

    Default usage (loads from bundled snapshot, no API call)::

        registry = CompanyRegistry.create()
        company = registry.by_ticker("7203")

    To refresh from EDINET API (requires edinet-mcp + API key)::

        registry = await CompanyRegistry.create_async()
    """

    def __init__(self, companies: Sequence[CompanyLike]) -> None:
        self._companies = companies
        self._by_edinet: dict[str, CompanyLike] = {}
        self._by_ticker: dict[str, CompanyLike] = {}
        self._by_sec_code: dict[str, CompanyLike] = {}
        self._by_corporate_number: dict[str, CompanyLike] = {}
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
    def create(cls) -> CompanyRegistry:
        """Load from the bundled snapshot (synchronous, no API call).

        This is the recommended way to create a registry. Uses the
        embedded company data shipped with this package.
        """
        companies_data, _metadata = load_snapshot()
        companies = [_CompanyRecord(**d) for d in companies_data]
        return cls(companies)

    @classmethod
    async def create_async(cls, *, api_key: str | None = None) -> CompanyRegistry:
        """Fetch the EDINET company list and build the registry.

        Requires ``edinet-mcp`` to be installed and an EDINET API key.

        Args:
            api_key: EDINET API key. If ``None``, reads from
                ``EDINET_API_KEY`` environment variable.
        """
        try:
            from edinet_mcp import EdinetClient
        except ImportError as e:
            raise ImportError(
                "edinet-mcp is required for live EDINET API access. "
                "Install it with: pip install edinet-mcp"
            ) from e
        async with EdinetClient(api_key=api_key or "") as client:
            companies = await client.search_companies("")
        return cls(companies)  # type: ignore[arg-type]  # edinet_mcp optional

    @classmethod
    def from_companies(cls, companies: Sequence[CompanyLike]) -> CompanyRegistry:
        """Build a registry from a pre-loaded company list."""
        return cls(companies)

    def by_edinet(self, edinet_code: str) -> CompanyLike | None:
        """Look up by EDINET code (e.g. ``"E02144"``)."""
        return self._by_edinet.get(edinet_code)

    def by_ticker(self, ticker: str) -> CompanyLike | None:
        """Look up by 4-digit ticker (e.g. ``"7203"``)."""
        return self._by_ticker.get(ticker)

    def by_sec_code(self, sec_code: str) -> CompanyLike | None:
        """Look up by 5-digit securities code (e.g. ``"72030"``)."""
        return self._by_sec_code.get(sec_code)

    def by_corporate_number(self, corporate_number: str) -> CompanyLike | None:
        """Look up by 13-digit corporate number / 法人番号."""
        return self._by_corporate_number.get(corporate_number)

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for fuzzy matching."""
        return unicodedata.normalize("NFKC", text).lower()

    def _score_match(self, name: str, tokens: list[str]) -> int:
        """Score how well *name* matches the search tokens."""
        normalized = self._normalize(name)
        for token in tokens:
            if token not in normalized:
                return 0
        if len(tokens) == 1:
            token = tokens[0]
            if normalized == token:
                return _SCORE_EXACT
            if normalized.startswith(token):
                return _SCORE_PREFIX
            return _SCORE_CONTAINS
        return _SCORE_CONTAINS

    def search(self, query: str, *, limit: int = 10) -> list[CompanyLike]:
        """Search companies by name with ranked fuzzy matching."""
        normalized_query = self._normalize(query)
        tokens = normalized_query.split()
        if not tokens:
            return []
        scored: list[tuple[int, CompanyLike]] = []
        for c in self._companies:
            best = self._score_match(c.name, tokens)
            if c.name_en:
                best = max(best, self._score_match(c.name_en, tokens))
            if best > 0:
                scored.append((best, c))
        scored.sort(key=lambda pair: (-pair[0], pair[1].name))
        return [c for _, c in scored[:limit]]

    def resolve(self, identifier: str) -> CompanyLike | None:
        """Auto-detect identifier type and look up."""
        if identifier.startswith("E") and len(identifier) == 6:
            return self.by_edinet(identifier)
        if len(identifier) == 4 and identifier.isdigit():
            return self.by_ticker(identifier)
        if len(identifier) == 5 and identifier.isdigit():
            return self.by_sec_code(identifier)
        if len(identifier) == 13 and identifier.isdigit():
            return self.by_corporate_number(identifier)
        return (
            self._by_edinet.get(identifier)
            or self._by_ticker.get(identifier)
            or self._by_sec_code.get(identifier)
            or self._by_corporate_number.get(identifier)
        )

    @property
    def companies(self) -> list[CompanyLike]:
        """All companies in the registry (shallow copy)."""
        return list(self._companies)

    def __len__(self) -> int:
        return len(self._companies)

    def __contains__(self, edinet_code: str) -> bool:
        return edinet_code in self._by_edinet
