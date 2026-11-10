"""x402 payTo source-of-truth tests (no parent x402 server required)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packs.x402_payto import (
    CANONICAL_PAY_TO,
    RETIRED_PAY_TO,
    USDC_BASE_ASSET,
    assert_pay_to_allowed,
    expected_payment_accept,
    is_retired_pay_to,
    resolve_pay_to,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RETIRED_FULL = "0xAB745e5F576667037696e78ba7dA28E193E4423D"
FUSION_MANIFEST = REPO_ROOT / "packs" / "fusion-panda-cyberpunk" / "manifest.json"

TEXT_GLOBS = ("*.md", "*.json", "*.py", "*.example", "*.yaml", "*.yml", "*.toml", "*.sh")


def _iter_repo_text_files() -> list[Path]:
    paths: list[Path] = []
    for pattern in TEXT_GLOBS:
        paths.extend(REPO_ROOT.rglob(pattern))
    skip = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}
    return [p for p in paths if p.is_file() and not any(part in skip for part in p.parts)]


def test_canonical_pay_to_is_keith_wallet():
    assert CANONICAL_PAY_TO == "0x0d25A44f74868eCE53B305C97139CF4B62963410"


def test_retired_address_rejected_case_insensitive():
    assert is_retired_pay_to(RETIRED_FULL)
    assert is_retired_pay_to(RETIRED_FULL.lower())
    with pytest.raises(ValueError, match="retired seller wallet"):
        assert_pay_to_allowed(RETIRED_FULL)


def test_resolve_pay_to_defaults_to_canonical(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("X402_PAY_TO_ADDRESS", raising=False)
    monkeypatch.delenv("X402_PAY_TO", raising=False)
    assert resolve_pay_to(None) == CANONICAL_PAY_TO


def test_resolve_pay_to_honors_env(monkeypatch: pytest.MonkeyPatch):
    custom = "0x1111111111111111111111111111111111111111"
    monkeypatch.setenv("X402_PAY_TO_ADDRESS", custom)
    assert resolve_pay_to(None) == custom


def test_fusion_manifest_advertises_keith_payto_and_base_usdc():
    data = json.loads(FUSION_MANIFEST.read_text(encoding="utf-8"))
    x402 = data["x402"]
    assert x402["pay_to"] == CANONICAL_PAY_TO
    assert x402["network"] == "eip155:8453"
    assert x402["asset"] == USDC_BASE_ASSET
    assert x402["scheme"] == "exact"
    assert x402["pay_to_env"] == "X402_PAY_TO_ADDRESS"


def test_expected_challenge_accept_matches_manifest_price():
    accept = expected_payment_accept(price_usdc="0.49")
    assert accept["payTo"] == CANONICAL_PAY_TO
    assert accept["network"] == "eip155:8453"
    assert accept["asset"] == USDC_BASE_ASSET
    assert accept["amount"] == "490000"
    assert accept["scheme"] == "exact"


def test_repo_contains_no_retired_payto_literals():
    needle = RETIRED_FULL.lower()
    offenders: list[str] = []
    for path in _iter_repo_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if needle in text.lower():
            rel = path.relative_to(REPO_ROOT)
            # Allowed: blocklist module, this test module, MEMORY "do not use" note
            if rel.as_posix() in {"packs/x402_payto.py", "tests/test_payto.py"}:
                continue
            if path.name == "MEMORY.md" and "Retired (never use)" in text:
                continue
            offenders.append(str(rel))
    assert offenders == [], f"retired payTo still present in: {offenders}"


def test_env_example_uses_canonical_not_retired():
    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert CANONICAL_PAY_TO in example
    assert RETIRED_FULL.lower() not in example.lower()


def test_retired_set_includes_documented_wallet():
    assert RETIRED_FULL.lower() in RETIRED_PAY_TO
