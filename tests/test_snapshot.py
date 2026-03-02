"""Tests for snapshot loading and verification."""

from __future__ import annotations

from japan_finance_codes import CompanyRegistry
from japan_finance_codes._snapshot import load_snapshot, verify_snapshot


class TestSnapshot:
    def test_load_snapshot_returns_companies(self) -> None:
        companies, metadata = load_snapshot()
        assert len(companies) > 0
        assert metadata["record_count"] == len(companies)

    def test_load_snapshot_has_metadata(self) -> None:
        _companies, metadata = load_snapshot()
        assert metadata["generated_at"] is not None
        assert metadata["sha256"] is not None
        assert metadata["source"] is not None

    def test_verify_snapshot_integrity(self) -> None:
        info = verify_snapshot()
        assert info["valid"] is True
        assert info["sha256_match"] is True
        assert info["record_count"] > 0
        assert info["age_days"] is not None

    def test_create_from_snapshot(self) -> None:
        """CompanyRegistry.create() should work without edinet-mcp."""
        registry = CompanyRegistry.create()
        assert len(registry) > 1000
        # Toyota should be in the registry
        toyota = registry.by_ticker("7203")
        assert toyota is not None
        assert toyota.edinet_code == "E02144"

    def test_search_from_snapshot(self) -> None:
        registry = CompanyRegistry.create()
        results = registry.search("トヨタ")
        assert len(results) > 0
        assert any(c.edinet_code == "E02144" for c in results)

    def test_resolve_from_snapshot(self) -> None:
        registry = CompanyRegistry.create()
        c = registry.resolve("7203")
        assert c is not None
        assert c.name == "トヨタ自動車株式会社"
