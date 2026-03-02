"""Embedded company registry snapshot loader.

Loads company data from the bundled JSON snapshot instead of
requiring a live EDINET API call. The snapshot is refreshed
periodically (see ``refresh`` CLI command).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import warnings
from datetime import datetime, timezone
from importlib import resources
from typing import Any

logger = logging.getLogger(__name__)

# Warn if snapshot is older than this many days
_STALENESS_WARNING_DAYS = 90


def _load_raw() -> dict[str, Any]:
    """Load the raw snapshot dict from the bundled gzip file."""
    data_pkg = resources.files("japan_finance_codes") / "_data"
    gz_path = data_pkg / "company_registry.json.gz"
    raw = gz_path.read_bytes()
    result: dict[str, Any] = json.loads(gzip.decompress(raw))
    return result


def load_snapshot() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load company records and metadata from the bundled snapshot.

    Returns:
        Tuple of (company_dicts, metadata_dict).
        metadata_dict has keys: generated_at, source, record_count, sha256.

    Raises:
        FileNotFoundError: If the snapshot file is missing.
    """
    snapshot = _load_raw()

    companies = snapshot.get("companies", [])
    metadata = {
        "generated_at": snapshot.get("generated_at"),
        "source": snapshot.get("source"),
        "record_count": snapshot.get("record_count", len(companies)),
        "sha256": snapshot.get("sha256"),
    }

    # Staleness warning
    generated_at = snapshot.get("generated_at")
    if generated_at:
        try:
            gen_dt = datetime.fromisoformat(generated_at)
            age_days = (datetime.now(timezone.utc) - gen_dt).days
            if age_days > _STALENESS_WARNING_DAYS:
                warnings.warn(
                    f"Company registry snapshot is {age_days} days old "
                    f"(generated {generated_at}). "
                    "Run 'japan-finance-codes refresh' to update.",
                    stacklevel=2,
                )
        except (ValueError, TypeError):
            pass

    return companies, metadata


def verify_snapshot() -> dict[str, Any]:
    """Verify snapshot integrity and return status info.

    Returns:
        Dict with keys: valid, record_count, generated_at, age_days, sha256_match.
    """
    snapshot = _load_raw()
    companies = snapshot.get("companies", [])
    stored_sha = snapshot.get("sha256", "")

    # Recompute hash
    data_for_hash = json.dumps(companies, ensure_ascii=False, sort_keys=True)
    computed_sha = hashlib.sha256(data_for_hash.encode()).hexdigest()
    sha_match = stored_sha == computed_sha

    # Age
    generated_at = snapshot.get("generated_at")
    age_days = None
    if generated_at:
        try:
            gen_dt = datetime.fromisoformat(generated_at)
            age_days = (datetime.now(timezone.utc) - gen_dt).days
        except (ValueError, TypeError):
            pass

    return {
        "valid": sha_match,
        "record_count": len(companies),
        "generated_at": generated_at,
        "age_days": age_days,
        "sha256_match": sha_match,
        "sha256": stored_sha[:16] + "..." if stored_sha else None,
    }
