"""Canonical x402 seller receive address for all packs in this repository."""

from __future__ import annotations

import os
import re
from typing import Final

# Keith's Base USDC receive wallet (Coinbase Base Account)
CANONICAL_PAY_TO: Final[str] = "0x0d25A44f74868eCE53B305C97139CF4B62963410"

# USDC on Base mainnet (EIP-20)
USDC_BASE_ASSET: Final[str] = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

BASE_MAINNET_CAIP2: Final[str] = "eip155:8453"

X402_PAY_TO_ENV_KEYS: Final[tuple[str, ...]] = ("X402_PAY_TO_ADDRESS", "X402_PAY_TO")

# Retired seller wallets — must never appear in challenges or env defaults.
RETIRED_PAY_TO: Final[frozenset[str]] = frozenset(
    {
        "0xab745e5f576667037696e78ba7da28e193e4423d",
        "0x05e1720bb82f86b5bc7940a99fdc702e32256357",
    }
)

_ETH_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def normalize_pay_to(addr: str | None) -> str | None:
    if not addr:
        return None
    cleaned = addr.strip()
    if not cleaned:
        return None
    return cleaned.lower()


def is_retired_pay_to(addr: str | None) -> bool:
    n = normalize_pay_to(addr)
    return bool(n and n in RETIRED_PAY_TO)


def assert_pay_to_allowed(addr: str | None) -> None:
    if is_retired_pay_to(addr):
        raise ValueError(
            f"payTo {addr!r} is a retired seller wallet and must not be used. "
            f"Set {X402_PAY_TO_ENV_KEYS[0]} to {CANONICAL_PAY_TO}."
        )


def resolve_pay_to(explicit: str | None = None) -> str:
    """Resolve seller payTo: explicit arg, then env, then canonical default."""
    for candidate in (
        explicit,
        *(os.getenv(key) for key in X402_PAY_TO_ENV_KEYS),
        CANONICAL_PAY_TO,
    ):
        if candidate and candidate.strip():
            addr = candidate.strip()
            assert_pay_to_allowed(addr)
            if not _ETH_ADDRESS_RE.match(addr):
                raise ValueError(f"Invalid Ethereum address: {addr!r}")
            return addr
    return CANONICAL_PAY_TO


def expected_payment_accept(*, pay_to: str | None = None, price_usdc: str = "0.49") -> dict[str, str | int]:
    """Shape of one `accepts[]` entry for pack catalog / tests (exact scheme, Base USDC)."""
    recipient = resolve_pay_to(pay_to)
    try:
        atomic = int(round(float(price_usdc) * 1_000_000))
    except ValueError as exc:
        raise ValueError(f"Invalid USDC amount: {price_usdc!r}") from exc
    return {
        "scheme": "exact",
        "network": BASE_MAINNET_CAIP2,
        "payTo": recipient,
        "pay_to": recipient,
        "asset": USDC_BASE_ASSET,
        "amount": str(atomic),
        "maxTimeoutSeconds": 300,
    }
