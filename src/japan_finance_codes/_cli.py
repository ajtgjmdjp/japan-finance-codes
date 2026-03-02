"""CLI for japan-finance-codes: info, verify, refresh."""

from __future__ import annotations

import json
import sys


def cli() -> None:
    """Simple CLI dispatcher (no click dependency)."""
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        _help()
    elif args[0] == "info":
        _info()
    elif args[0] == "verify":
        _verify()
    elif args[0] == "refresh":
        _refresh()
    elif args[0] == "--version":
        from japan_finance_codes import __version__

        print(f"japan-finance-codes {__version__}")
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        _help()
        sys.exit(1)


def _help() -> None:
    print(
        "japan-finance-codes: Company ID registry for Japanese financial data\n"
        "\n"
        "Commands:\n"
        "  info      Show snapshot metadata (age, record count, hash)\n"
        "  verify    Verify snapshot integrity (SHA-256 check)\n"
        "  refresh   Download fresh data from EDINET API (requires edinet-mcp)\n"
        "  --version Show version\n"
    )


def _info() -> None:
    from japan_finance_codes._snapshot import verify_snapshot

    info = verify_snapshot()
    print(f"Records:      {info['record_count']}")
    print(f"Generated at: {info['generated_at']}")
    print(f"Age:          {info['age_days']} days")
    print(f"SHA-256:      {info['sha256']}")
    print(f"Integrity:    {'OK' if info['sha256_match'] else 'MISMATCH'}")


def _verify() -> None:
    from japan_finance_codes._snapshot import verify_snapshot

    info = verify_snapshot()
    if info["sha256_match"]:
        print(f"OK: {info['record_count']} records, integrity verified")
    else:
        print("FAIL: SHA-256 mismatch — snapshot may be corrupted", file=sys.stderr)
        sys.exit(1)


def _refresh() -> None:
    try:
        import asyncio

        from edinet_mcp import EdinetClient
    except ImportError:
        print(
            "edinet-mcp is required for refresh.\n"
            "Install with: pip install japan-finance-codes[refresh]",
            file=sys.stderr,
        )
        sys.exit(1)

    import gzip
    import hashlib
    from datetime import datetime, timezone
    from pathlib import Path

    # Resolve the _data directory relative to the package source.
    # Works for both editable installs and normal wheel installs.
    _pkg_dir = Path(__file__).resolve().parent
    _data_dir = _pkg_dir / "_data"
    if not _data_dir.is_dir():
        print(
            f"Cannot find _data directory at {_data_dir}.\n"
            "Refresh is only supported for editable (development) installs.",
            file=sys.stderr,
        )
        sys.exit(1)
    gz_path = _data_dir / "company_registry.json.gz"
    if not gz_path.exists():
        print(
            f"Snapshot file not found at {gz_path}.",
            file=sys.stderr,
        )
        sys.exit(1)

    async def _do_refresh() -> int:
        async with EdinetClient() as client:
            companies = await client.search_companies("")

        records = []
        for c in companies:
            d = c.model_dump()
            std = d.get("accounting_standard")
            if std is not None and hasattr(std, "value"):
                d["accounting_standard"] = std.value
            records.append(d)

        data_for_hash = json.dumps(records, ensure_ascii=False, sort_keys=True)
        sha = hashlib.sha256(data_for_hash.encode()).hexdigest()

        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "EDINET code list (Edinetcode.zip)",
            "record_count": len(records),
            "sha256": sha,
            "companies": records,
        }

        raw = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode()
        # Atomic write: write to temp file, then rename
        tmp_path = gz_path.with_suffix(".tmp")
        with gzip.open(tmp_path, "wb") as f:
            f.write(raw)
        tmp_path.rename(gz_path)

        print(f"Refreshed: {len(records)} companies, sha256={sha[:16]}...")
        return len(records)

    asyncio.run(_do_refresh())
