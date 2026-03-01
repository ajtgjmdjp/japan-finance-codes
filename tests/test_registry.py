"""Tests for CompanyRegistry."""

from __future__ import annotations

from edinet_mcp.models import Company

from japan_finance_codes import CompanyRegistry


class TestLookup:
    def test_by_edinet(self, registry: CompanyRegistry) -> None:
        c = registry.by_edinet("E02144")
        assert c is not None
        assert c.name == "トヨタ自動車株式会社"

    def test_by_edinet_not_found(self, registry: CompanyRegistry) -> None:
        assert registry.by_edinet("E99999") is None

    def test_by_ticker(self, registry: CompanyRegistry) -> None:
        c = registry.by_ticker("6758")
        assert c is not None
        assert c.edinet_code == "E01777"

    def test_by_ticker_not_found(self, registry: CompanyRegistry) -> None:
        assert registry.by_ticker("9999") is None

    def test_by_sec_code(self, registry: CompanyRegistry) -> None:
        c = registry.by_sec_code("72030")
        assert c is not None
        assert c.edinet_code == "E02144"

    def test_by_corporate_number(self, registry: CompanyRegistry) -> None:
        c = registry.by_corporate_number("7010401067252")
        assert c is not None
        assert c.name == "ソニーグループ株式会社"

    def test_by_corporate_number_unlisted(self, registry: CompanyRegistry) -> None:
        c = registry.by_corporate_number("1234567890123")
        assert c is not None
        assert c.is_listed is False


class TestResolve:
    def test_resolve_edinet_code(self, registry: CompanyRegistry) -> None:
        c = registry.resolve("E02144")
        assert c is not None
        assert c.ticker == "7203"

    def test_resolve_ticker(self, registry: CompanyRegistry) -> None:
        c = registry.resolve("7203")
        assert c is not None
        assert c.edinet_code == "E02144"

    def test_resolve_sec_code(self, registry: CompanyRegistry) -> None:
        c = registry.resolve("72030")
        assert c is not None
        assert c.edinet_code == "E02144"

    def test_resolve_corporate_number(self, registry: CompanyRegistry) -> None:
        c = registry.resolve("2180001012461")
        assert c is not None
        assert c.edinet_code == "E02144"

    def test_resolve_unknown(self, registry: CompanyRegistry) -> None:
        assert registry.resolve("unknown_string") is None


class TestSearch:
    def test_search_japanese_name(self, registry: CompanyRegistry) -> None:
        results = registry.search("トヨタ")
        assert len(results) == 1
        assert results[0].edinet_code == "E02144"

    def test_search_english_name(self, registry: CompanyRegistry) -> None:
        results = registry.search("Sony")
        assert len(results) == 1
        assert results[0].edinet_code == "E01777"

    def test_search_case_insensitive(self, registry: CompanyRegistry) -> None:
        results = registry.search("toyota")
        assert len(results) == 1

    def test_search_no_match(self, registry: CompanyRegistry) -> None:
        results = registry.search("存在しない企業")
        assert len(results) == 0

    def test_search_limit(self, registry: CompanyRegistry) -> None:
        results = registry.search("株式会社", limit=2)
        assert len(results) == 2

    def test_search_partial(self, registry: CompanyRegistry) -> None:
        results = registry.search("グループ")
        assert len(results) == 1
        assert results[0].name == "ソニーグループ株式会社"

    def test_search_nfkc_halfwidth(self, registry: CompanyRegistry) -> None:
        """Half-width katakana should match full-width."""
        results = registry.search("ﾄﾖﾀ")
        assert len(results) == 1
        assert results[0].edinet_code == "E02144"

    def test_search_multi_token(self, registry: CompanyRegistry) -> None:
        """Space-separated tokens should AND match."""
        results = registry.search("トヨタ 自動車")
        assert len(results) == 1
        assert results[0].edinet_code == "E02144"

    def test_search_multi_token_no_match(self, registry: CompanyRegistry) -> None:
        """Multi-token where one token doesn't match returns nothing."""
        results = registry.search("トヨタ 電気")
        assert len(results) == 0

    def test_search_ranking_exact_over_contains(self) -> None:
        """Exact name match should rank higher than partial match."""
        companies = [
            Company(edinet_code="E00001", name="ABC株式会社", is_listed=True),
            Company(edinet_code="E00002", name="ABC", is_listed=True),
        ]
        r = CompanyRegistry.from_companies(companies)
        results = r.search("abc")
        assert len(results) == 2
        # Exact match should be first
        assert results[0].edinet_code == "E00002"

    def test_search_ranking_prefix_over_contains(self) -> None:
        """Prefix match should rank higher than contains match."""
        companies = [
            Company(edinet_code="E00001", name="XXXソニーXXX", is_listed=True),
            Company(edinet_code="E00002", name="ソニーXXX", is_listed=True),
        ]
        r = CompanyRegistry.from_companies(companies)
        results = r.search("ソニー")
        assert len(results) == 2
        assert results[0].edinet_code == "E00002"  # prefix

    def test_search_empty_query(self, registry: CompanyRegistry) -> None:
        """Empty query returns nothing."""
        results = registry.search("")
        assert len(results) == 0

    def test_search_fullwidth_alpha(self, registry: CompanyRegistry) -> None:
        """Full-width 'ＳＯＮＹ' should match 'Sony'."""
        results = registry.search("ＳＯＮＹ")
        assert len(results) == 1
        assert results[0].edinet_code == "E01777"


class TestRegistryMeta:
    def test_len(self, registry: CompanyRegistry) -> None:
        assert len(registry) == 3

    def test_contains(self, registry: CompanyRegistry) -> None:
        assert "E02144" in registry
        assert "E99999" not in registry

    def test_companies_property(self, registry: CompanyRegistry) -> None:
        assert len(registry.companies) == 3

    def test_from_companies(self, sample_companies: list[Company]) -> None:
        r = CompanyRegistry.from_companies(sample_companies)
        assert len(r) == 3

    def test_empty_registry(self) -> None:
        r = CompanyRegistry.from_companies([])
        assert len(r) == 0
        assert r.by_ticker("7203") is None
        assert r.resolve("E02144") is None
        assert r.search("トヨタ") == []

    def test_unlisted_no_ticker_index(self, registry: CompanyRegistry) -> None:
        """Unlisted company without ticker is not in ticker index."""
        assert registry.by_ticker("") is None
