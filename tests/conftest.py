"""Shared test fixtures for japan-finance-codes."""

from __future__ import annotations

import pytest

from japan_finance_codes import CompanyRegistry
from japan_finance_codes._registry import _CompanyRecord


@pytest.fixture()
def sample_companies() -> list[_CompanyRecord]:
    return [
        _CompanyRecord(
            edinet_code="E02144",
            name="トヨタ自動車株式会社",
            name_en="Toyota Motor Corporation",
            ticker="7203",
            sec_code="72030",
            corporate_number="2180001012461",
            industry="輸送用機器",
            accounting_standard="ifrs",
            is_listed=True,
        ),
        _CompanyRecord(
            edinet_code="E01777",
            name="ソニーグループ株式会社",
            name_en="Sony Group Corporation",
            ticker="6758",
            sec_code="67580",
            corporate_number="7010401067252",
            industry="電気機器",
            accounting_standard="ifrs",
            is_listed=True,
        ),
        _CompanyRecord(
            edinet_code="E31000",
            name="テスト非上場株式会社",
            corporate_number="1234567890123",
            is_listed=False,
        ),
    ]


@pytest.fixture()
def registry(sample_companies: list[_CompanyRecord]) -> CompanyRegistry:
    return CompanyRegistry.from_companies(sample_companies)
