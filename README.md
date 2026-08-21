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
- **Key Features:** Supports multi-provider execution (OpenAI DALL-E 3, Replicate Flux/SDXL, and a local SVG vector fallback).
