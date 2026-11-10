# x402 MCP Packs 📦

A modular repository for packaging and distributing x402-enabled MCP (Model Context Protocol) tool packs. These packs enable AI agents to purchase prompt kits and digital generation services using micro-payments.

## Structure
- `/packs`: Contains structured, modular prompt packs and generation tools.
  - `{{pack-name}}/manifest.json`: Configuration defining SKU, pricing, chain networks, and parameters.
  - `{{pack-name}}/pack.py`: Image generation prompt structures, preset definitions, and generation client integrations.
- `/templates`: Scaffold files for spinning up new packs.

## Available Packs

### 1. Fusion Panda Cyberpunk Poster Pack (`merchforge-fusion-panda-poster-kit-v1`)
A high-quality cyberpunk poster prompt generator featuring 125 preset aesthetic combinations.
- **Price:** $0.49 USDC
- **Chain:** Base (`eip155:8453`)
- **Asset:** USDC on Base (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
- **payTo (default):** `0x0d25A44f74868eCE53B305C97139CF4B62963410` — override only via `X402_PAY_TO_ADDRESS` on the parent x402 HTTP server (see `.env.example`).
- **Key Features:** Supports multi-provider execution (OpenAI DALL-E 3, Replicate Flux/SDXL, and a local SVG vector fallback).

## x402 payments

Pack manifests and `packs/x402_payto.py` define the canonical seller wallet. **HTTP 402 challenges are built by the parent app** (for example [alpha-sentinel-mcp](https://github.com/kwizzlesurp10-ctrl/alpha-sentinel-mcp)) using `settings.x402_pay_to_address` from `X402_PAY_TO_ADDRESS`.

| Variable | Required on deploy | Notes |
|----------|-------------------|-------|
| `X402_PAY_TO_ADDRESS` | Yes (production) | Must be Keith's wallet above; retired `0xAB745e5F…4423D` must not be used |
| `X402_PAY_TO` | Optional alias | Same as above if your host reads this name |

Run pack payment metadata tests: `pytest tests/test_payto.py -v`
