# japan-finance-codes

> **Status: Maintenance mode** — This project is stable and functional but not actively developed. Issues and PRs are welcome.


Unified company ID registry for Japanese financial data.

Maps between EDINET codes, securities codes (4/5-digit), corporate numbers (法人番号), and yfinance tickers.

## Installation

```bash
pip install japan-finance-codes
```

## Usage

```python
from japan_finance_codes import CompanyRegistry

# Build registry from EDINET company list
registry = await CompanyRegistry.create()

# Lookup by various ID types
company = registry.by_ticker("7203")           # 4-digit ticker
company = registry.by_edinet("E02144")         # EDINET code
company = registry.by_sec_code("72030")        # 5-digit securities code
company = registry.by_corporate_number("2180001012461")  # 法人番号

# Auto-detect identifier type
company = registry.resolve("7203")

# Name search
results = registry.search("トヨタ")
```

## License

Apache-2.0
