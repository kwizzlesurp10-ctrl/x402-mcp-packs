"""Fusion Panda Cyberpunk Poster Prompt Pack Engine.

Product ID: merchforge-fusion-panda-poster-kit-v1
Priced at $0.49 USDC on Base (eip155:8453).

Provides preset configuration, modular cyberpunk prompt assembly, multi-provider
image generation (OpenAI DALL-E 3, Replicate Flux/SDXL, and deterministic SVG mock),
x402 seller challenge building, payment verification/settlement, and commerce response formatting.
"""

from __future__ import annotations

import html
import logging
import urllib.parse
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger("x402.fusion_panda")

# ---- Product & Commerce Constants ------------------------------------------

PRODUCT_ID = "merchforge-fusion-panda-poster-kit-v1"
SKU = "MF-FUSION-PANDA-POSTER-V1"
PRICE_USD = 0.49
PRICE_USDC = 0.49
LICENSE = "Commercial Merch & Digital Print License (Single Output)"
ATTRIBUTION = "Generated via MerchForge on x402-mcp"

SERVICE_NAME = "Fusion Panda Poster"
SERVICE_TAGS = ["merch", "poster", "cyberpunk", "ai-art", "panda"]

RESOURCE_DESCRIPTION = (
    "Generate high-resolution cyberpunk-style Fusion Panda posters for merch "
    "and digital print using AI image generation. POST JSON with style, colorway, "
    "pose, aspect_ratio. Free sample: /poster/fusion-panda/sample."
)

# ---- Presets ---------------------------------------------------------------

STYLE_PRESETS: dict[str, str] = {
    "cyberpunk_classic": (
        "Gritty neon metropolis, rain-slicked asphalt streets reflecting neon signs, "
        "glowing holographic kanji advertisements, chrome cybernetic visor, "
        "high-contrast volumetric neon lighting, cinematic depth of field, 8k resolution"
    ),
    "synthwave_retro": (
        "1980s retro-futuristic synthwave aesthetic, glowing wireframe grid horizon, "
        "magenta and cyan gradient dusk sky, chrome reflections, analog synthesizer atmosphere, "
        "VHS scanline accents, retro outrun vibe"
    ),
    "techwear_tactical": (
        "Tactical urban techwear combat gear, matte-black modular loadout harness, "
        "utility pouches, digital camouflage textures, military HUD optical overlay, "
        "carbon-fiber armor plating, stealth aesthetic"
    ),
    "mecha_fusion": (
        "Heavy industrial mecha exoskeleton armor, glowing plasma conduit tubes, "
        "reinforced titanium shoulder plating, hydraulic cybernetic joints, "
        "steam exhaust vents, high-tech engineering"
    ),
    "neo_tokyo_ink": (
        "Dynamic Japanese sumi-e brush calligraphy blended with vivid street graffiti, "
        "splatter ink aesthetics, high-energy brushstrokes, stencil overlays, "
        "dystopian urban alley backdrop, mixed media fusion"
    ),
}

COLORWAY_PRESETS: dict[str, dict[str, Any]] = {
    "neon_noir": {
        "description": "Electric cyan (#00F0FF), vibrant hot magenta (#FF007F), deep midnight indigo, pitch obsidian black",
        "primary": "#00F0FF",
        "secondary": "#FF007F",
        "bg_start": "#0A0B1E",
        "bg_end": "#020308",
        "accent": "#00F0FF",
    },
    "acid_hazard": {
        "description": "Toxic radioactive green (#39FF14), hazard warning amber yellow (#FFD700), industrial charcoal grey, high-contrast dark backdrop",
        "primary": "#39FF14",
        "secondary": "#FFD700",
        "bg_start": "#111812",
        "bg_end": "#050805",
        "accent": "#39FF14",
    },
    "vapor_sunset": {
        "description": "Pastel violet (#9D4EDD), sunset coral pink (#FF70A6), retro turquoise teal (#70D6FF), warm golden dusk gradient",
        "primary": "#FF70A6",
        "secondary": "#70D6FF",
        "bg_start": "#24103A",
        "bg_end": "#0C0414",
        "accent": "#FFD166",
    },
    "obsidian_gold": {
        "description": "Matte stealth black (#121212), polished 24k brushed gold accents (#FFD700), warm amber glow, luxury high-contrast lighting",
        "primary": "#FFD700",
        "secondary": "#FFB703",
        "bg_start": "#1A1A1A",
        "bg_end": "#080808",
        "accent": "#FFAA00",
    },
    "hyper_violet": {
        "description": "Deep ultraviolet (#7B2CBF), electric violet-purple (#C77DFF), neon blue accents (#3A86FF), glowing radioactive cyan highlights",
        "primary": "#C77DFF",
        "secondary": "#3A86FF",
        "bg_start": "#19082B",
        "bg_end": "#05010B",
        "accent": "#00F0FF",
    },
}

POSE_PRESETS: dict[str, str] = {
    "heroic_standing": (
        "Dynamic low-angle 3/4 heroic power stance, brandishing a glowing high-frequency cyber katana, "
        "confident gaze piercing through dense neon fog"
    ),
    "action_leap": (
        "Mid-air acrobatic dynamic combat strike, energy slash light trail curving through the frame, "
        "flying electric sparks, dynamic motion lines"
    ),
    "hacker_crouch": (
        "Low tactical rooftop crouch overlooking a sprawling skyline, operating floating holographic "
        "terminal screens with deployed recon drones"
    ),
    "street_portrait": (
        "Close-up cinematic portrait, intricate cybernetic eye implant with glowing targeting reticle, "
        "lowered tactical respirator mask, rain droplets on fur and chrome"
    ),
    "meditating_zen": (
        "Floating in zero-gravity lotus position, glowing cyber-chakra energy nodes, "
        "surrounded by holographic digital bamboo in a digital cyberspace void"
    ),
}

ASPECT_RATIO_MAP: dict[str, tuple[str, str]] = {
    "1024x1792": ("1024x1792", "9:16"),
    "9:16": ("1024x1792", "9:16"),
    "1024x1024": ("1024x1024", "1:1"),
    "1:1": ("1024x1024", "1:1"),
    "1792x1024": ("1792x1024", "16:9"),
    "16:9": ("1792x1024", "16:9"),
}


class ImageGenerationError(Exception):
    """Custom error raised when an image generation API request fails."""

    def __init__(self, code: str, detail: str, status_code: int = 502) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


def normalize_aspect_ratio(aspect_ratio: str) -> tuple[str, str]:
    """Normalize aspect ratio into (openai_dimensions, replicate_ratio)."""
    clean = aspect_ratio.strip().lower()
    return ASPECT_RATIO_MAP.get(clean, ("1024x1792", "9:16"))


# ---- Prompt Builder --------------------------------------------------------


def build_fusion_panda_prompt(
    style: str = "cyberpunk_classic",
    colorway: str = "neon_noir",
    pose: str = "heroic_standing",
    aspect_ratio: str = "1024x1792",
    custom_prompt: str | None = None,
    text_overlay: str | None = None,
) -> str:
    """Assemble a rich cyberpunk prompt from modular prompt pack presets."""
    if style not in STYLE_PRESETS:
        raise ValueError(
            f"Unknown style '{style}'. Supported styles: {', '.join(STYLE_PRESETS.keys())}"
        )
    if colorway not in COLORWAY_PRESETS:
        raise ValueError(
            f"Unknown colorway '{colorway}'. Supported colorways: {', '.join(COLORWAY_PRESETS.keys())}"
        )
    if pose not in POSE_PRESETS:
        raise ValueError(
            f"Unknown pose '{pose}'. Supported poses: {', '.join(POSE_PRESETS.keys())}"
        )

    pose_desc = POSE_PRESETS[pose]
    style_desc = STYLE_PRESETS[style]
    colorway_desc = COLORWAY_PRESETS[colorway]["description"]

    parts = [
        "Masterpiece cyberpunk graphic art poster featuring an anthropomorphic cyber-panda warrior "
        "with stylized cybernetic fur markings, glowing carbon-fiber armor, and high-tech implants.",
        f"Subject Pose & Composition: {pose_desc}.",
        f"Aesthetic Visual Style: {style_desc}.",
        f"Colorway Palette: {colorway_desc}.",
    ]

    if text_overlay and text_overlay.strip():
        clean_text = text_overlay.strip()
        parts.append(
            f'Poster Typography: Distinctive futuristic cyberpunk title typography displaying "{clean_text}" '
            'seamlessly integrated into the poster layout.'
        )

    if custom_prompt and custom_prompt.strip():
        parts.append(f"Custom Aesthetic Detail: {custom_prompt.strip()}.")

    parts.append(
        "Art Direction: Crisp vector-like line work, bold graphic design layout, cinematic volumetric "
        "lighting, high-contrast poster typography composition, 8k resolution, octane render quality."
    )

    return " ".join(parts)


# ---- Image Generation Client Providers -------------------------------------


async def _generate_openai(
    prompt: str,
    size: str = "1024x1792",
    api_key: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Generate image via OpenAI DALL-E 3 REST API."""
    key = api_key or settings.openai_api_key
    if not key:
        raise ValueError("OPENAI_API_KEY is not configured")

    req_timeout = timeout or settings.image_generator_timeout_seconds
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": size if size in ("1024x1024", "1024x1792", "1792x1024") else "1024x1792",
        "quality": "standard",
        "response_format": "url",
    }

    try:
        async with httpx.AsyncClient(timeout=req_timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise ImageGenerationError(
            code="upstream_timeout",
            detail=f"OpenAI generation timed out after {req_timeout}s",
            status_code=504,
        ) from exc
    except httpx.RequestError as exc:
        raise ImageGenerationError(
            code="upstream_connection_error",
            detail=f"Connection error reaching OpenAI: {exc}",
            status_code=502,
        ) from exc

    if response.status_code == 200:
        data = response.json()
        item = data.get("data", [{}])[0]
        return {
            "image_url": item.get("url"),
            "revised_prompt": item.get("revised_prompt", prompt),
            "provider": "openai",
            "model": "dall-e-3",
        }

    # Error handling
    err_body = {}
    try:
        err_body = response.json().get("error", {})
    except Exception:
        pass
    err_msg = err_body.get("message", response.text)

    if response.status_code == 401:
        raise ImageGenerationError(
            code="invalid_api_key",
            detail=f"Invalid or unauthorized OpenAI API key: {err_msg}",
            status_code=401,
        )
    if response.status_code == 429:
        raise ImageGenerationError(
            code="rate_limit_exceeded",
            detail=f"OpenAI rate limit or quota exceeded: {err_msg}",
            status_code=429,
        )
    if response.status_code == 400:
        is_safety = "safety" in err_msg.lower() or "policy" in err_msg.lower()
        raise ImageGenerationError(
            code="prompt_policy_violation" if is_safety else "bad_request",
            detail=f"OpenAI rejected request: {err_msg}",
            status_code=400,
        )

    raise ImageGenerationError(
        code="upstream_image_generator_unavailable",
        detail=f"OpenAI error (HTTP {response.status_code}): {err_msg}",
        status_code=502,
    )


async def _generate_replicate(
    prompt: str,
    aspect_ratio: str = "9:16",
    api_token: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Generate image via Replicate Flux/SDXL REST API."""
    token = api_token or settings.replicate_api_token
    if not token:
        raise ValueError("REPLICATE_API_TOKEN is not configured")

    req_timeout = timeout or settings.image_generator_timeout_seconds
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio if aspect_ratio in ("9:16", "1:1", "16:9") else "9:16",
            "output_format": "webp",
        }
    }

    try:
        async with httpx.AsyncClient(timeout=req_timeout) as client:
            response = await client.post(
                "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
                headers=headers,
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise ImageGenerationError(
            code="upstream_timeout",
            detail=f"Replicate generation timed out after {req_timeout}s",
            status_code=504,
        ) from exc
    except httpx.RequestError as exc:
        raise ImageGenerationError(
            code="upstream_connection_error",
            detail=f"Connection error reaching Replicate: {exc}",
            status_code=502,
        ) from exc

    if response.status_code in (200, 201):
        pred = response.json()
        status = pred.get("status")
        if status == "succeeded":
            output = pred.get("output")
            image_url = output[0] if isinstance(output, list) else str(output)
            return {
                "image_url": image_url,
                "revised_prompt": prompt,
                "provider": "replicate",
                "model": "black-forest-labs/flux-schnell",
            }
        if status in ("failed", "canceled"):
            raise ImageGenerationError(
                code="generation_failed",
                detail=f"Replicate prediction {status}: {pred.get('error')}",
                status_code=502,
            )

    err_body = {}
    try:
        err_body = response.json()
    except Exception:
        pass
    err_msg = err_body.get("detail", response.text)

    if response.status_code == 401:
        raise ImageGenerationError(
            code="invalid_api_key",
            detail=f"Invalid Replicate API token: {err_msg}",
            status_code=401,
        )
    if response.status_code == 429:
        raise ImageGenerationError(
            code="rate_limit_exceeded",
            detail=f"Replicate rate limit exceeded: {err_msg}",
            status_code=429,
        )

    raise ImageGenerationError(
        code="upstream_image_generator_unavailable",
        detail=f"Replicate error (HTTP {response.status_code}): {err_msg}",
        status_code=502,
    )


def _generate_mock(
    prompt: str,
    style: str,
    colorway: str,
    pose: str,
    aspect_ratio: str,
    text_overlay: str | None = None,
) -> dict[str, Any]:
    """Deterministic offline vector SVG generator producing complete cyberpunk poster graphic."""
    cw = COLORWAY_PRESETS.get(colorway, COLORWAY_PRESETS["neon_noir"])
    p_color = cw["primary"]
    s_color = cw["secondary"]
    accent_color = cw.get("accent", p_color)
    bg_start = cw["bg_start"]
    bg_end = cw["bg_end"]

    dims, _ = normalize_aspect_ratio(aspect_ratio)
    width, height = (1024, 1792) if dims == "1024x1792" else ((1024, 1024) if dims == "1024x1024" else (1792, 1024))

    title_text = html.escape((text_overlay or "FUSION PANDA 2099").upper())
    style_label = html.escape(style.replace("_", " ").upper())
    colorway_label = html.escape(colorway.replace("_", " ").upper())
    pose_label = html.escape(pose.replace("_", " ").upper())

    # Build genuine cyberpunk SVG poster with grid, panda geometry, implants, HUD, kanji and badges
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{bg_start}" />
      <stop offset="100%" stop-color="{bg_end}" />
    </linearGradient>
    <linearGradient id="neonGlow" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{p_color}" />
      <stop offset="100%" stop-color="{s_color}" />
    </linearGradient>
    <linearGradient id="visorGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{p_color}" stop-opacity="0.9" />
      <stop offset="100%" stop-color="{s_color}" stop-opacity="0.7" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="{width}" height="{height}" fill="url(#bg)" />

  <!-- Cyber Grid Horizon -->
  <g opacity="0.25" stroke="{p_color}" stroke-width="1.5">
    <line x1="0" y1="{height * 0.75}" x2="{width}" y2="{height * 0.75}" />
    <line x1="0" y1="{height * 0.82}" x2="{width}" y2="{height * 0.82}" />
    <line x1="0" y1="{height * 0.90}" x2="{width}" y2="{height * 0.90}" />
    <line x1="0" y1="{height * 0.97}" x2="{width}" y2="{height * 0.97}" />
    <line x1="{width * 0.5}" y1="{height * 0.70}" x2="{width * 0.1}" y2="{height}" />
    <line x1="{width * 0.5}" y1="{height * 0.70}" x2="{width * 0.3}" y2="{height}" />
    <line x1="{width * 0.5}" y1="{height * 0.70}" x2="{width * 0.5}" y2="{height}" />
    <line x1="{width * 0.5}" y1="{height * 0.70}" x2="{width * 0.7}" y2="{height}" />
    <line x1="{width * 0.5}" y1="{height * 0.70}" x2="{width * 0.9}" y2="{height}" />
  </g>

  <!-- Poster Border & Tech Frame -->
  <rect x="30" y="30" width="{width - 60}" height="{height - 60}" fill="none" stroke="{p_color}" stroke-width="2" opacity="0.6" />
  <rect x="45" y="45" width="{width - 90}" height="{height - 90}" fill="none" stroke="{s_color}" stroke-width="1" opacity="0.3" stroke-dasharray="8 6" />

  <!-- Cyberpunk Kanji & Header Accents -->
  <text x="60" y="90" font-family="monospace" font-size="20" fill="{p_color}" letter-spacing="4" filter="url(#glow)">サイバーパンク // MERCHFORGE-PROMPT-PACK-V1</text>
  <text x="{width - 60}" y="90" text-anchor="end" font-family="monospace" font-size="16" fill="{accent_color}">[SYS: ONLINE 2099]</text>

  <!-- Stylized Cyber Panda Character Silhouette & Implants -->
  <g transform="translate({width * 0.5}, {height * 0.48})">
    <!-- Outer Glow Halo / Cyber Sun -->
    <circle cx="0" cy="-40" r="{min(width, height) * 0.28}" fill="none" stroke="url(#neonGlow)" stroke-width="3" opacity="0.4" filter="url(#glow)" stroke-dasharray="16 8" />

    <!-- Panda Ears -->
    <circle cx="-140" cy="-190" r="70" fill="#12131A" stroke="{s_color}" stroke-width="4" />
    <circle cx="-140" cy="-190" r="45" fill="{s_color}" opacity="0.3" />
    <circle cx="140" cy="-190" r="70" fill="#12131A" stroke="{s_color}" stroke-width="4" />
    <circle cx="140" cy="-190" r="45" fill="{s_color}" opacity="0.3" />

    <!-- Head Base -->
    <ellipse cx="0" cy="-80" rx="170" ry="150" fill="#181A24" stroke="{p_color}" stroke-width="4" filter="url(#glow)" />

    <!-- Eye Patches (Cybernetic) -->
    <ellipse cx="-75" cy="-85" rx="55" ry="42" fill="#0A0B10" transform="rotate(-15 -75 -85)" stroke="{s_color}" stroke-width="2" />
    <ellipse cx="75" cy="-85" rx="55" ry="42" fill="#0A0B10" transform="rotate(15 75 -85)" stroke="{s_color}" stroke-width="2" />

    <!-- Glowing Cyber Visor -->
    <polygon points="-110,-95 110,-95 95,-45 -95,-45" fill="url(#visorGrad)" stroke="{p_color}" stroke-width="2" filter="url(#glow)" />
    <line x1="-100" y1="-70" x2="100" y2="-70" stroke="#FFFFFF" stroke-width="2" opacity="0.8" />
    <circle cx="-50" cy="-70" r="4" fill="#FFFFFF" filter="url(#glow)" />
    <circle cx="50" cy="-70" r="4" fill="#FFFFFF" filter="url(#glow)" />

    <!-- Cyber Snout & Mouth -->
    <ellipse cx="0" cy="-15" rx="42" ry="30" fill="#0E1017" stroke="{p_color}" stroke-width="1.5" />
    <polygon points="0,-25 -14,-35 14,-35" fill="{accent_color}" />
    <path d="M -15,-5 Q 0,8 15,-5" fill="none" stroke="{p_color}" stroke-width="2" />

    <!-- Neck Armor & Techwear Collar -->
    <path d="M -110,60 L 110,60 L 140,160 L -140,160 Z" fill="#0D0E15" stroke="{p_color}" stroke-width="3" />
    <line x1="-80" y1="80" x2="-80" y2="140" stroke="{s_color}" stroke-width="3" />
    <line x1="80" y1="80" x2="80" y2="140" stroke="{s_color}" stroke-width="3" />
    <circle cx="0" cy="110" r="16" fill="{accent_color}" filter="url(#glow)" />

    <!-- Cyber Katana / Power Energy Line -->
    <line x1="-220" y1="180" x2="220" y2="-220" stroke="url(#neonGlow)" stroke-width="5" filter="url(#glow)" />
  </g>

  <!-- Typography & Layout Metadata -->
  <g transform="translate({width * 0.5}, {height * 0.82})" text-anchor="middle">
    <!-- Main Title Banner -->
    <text y="0" font-family="system-ui, -apple-system, sans-serif" font-weight="900" font-size="{min(width * 0.07, 56.0)}" fill="url(#neonGlow)" letter-spacing="6" filter="url(#glow)">{title_text}</text>

    <!-- Metadata Chips -->
    <text y="45" font-family="monospace" font-size="18" fill="{accent_color}" letter-spacing="3">
      STYLE: {style_label}  |  COLORWAY: {colorway_label}
    </text>
    <text y="75" font-family="monospace" font-size="16" fill="#A0A5C0" letter-spacing="2">
      POSE: {pose_label}  |  RES: {dims}  |  SKU: {SKU}
    </text>
    <text y="105" font-family="monospace" font-size="14" fill="{p_color}" opacity="0.8">
      AUTHENTICATED ON-CHAIN VIA X402 PROTOCOL ($0.49 USDC ON BASE)
    </text>
  </g>
</svg>"""

    encoded_svg = urllib.parse.quote(svg_content.strip())
    data_uri = f"data:image/svg+xml;utf8,{encoded_svg}"

    return {
        "image_url": data_uri,
        "revised_prompt": prompt,
        "provider": "mock",
        "model": "merchforge-svg-engine-v1",
    }


# ---- High-level Poster Generator -------------------------------------------


async def generate_poster(
    style: str = "cyberpunk_classic",
    colorway: str = "neon_noir",
    pose: str = "heroic_standing",
    aspect_ratio: str = "1024x1792",
    custom_prompt: str | None = None,
    text_overlay: str | None = None,
    generator: str | None = None,
    mock: bool = False,
    network: str | None = None,
) -> dict[str, Any]:
    """Generate high-resolution cyberpunk Fusion Panda poster with full commerce metadata."""
    prompt = build_fusion_panda_prompt(
        style=style,
        colorway=colorway,
        pose=pose,
        aspect_ratio=aspect_ratio,
        custom_prompt=custom_prompt,
        text_overlay=text_overlay,
    )

    dims, ratio = normalize_aspect_ratio(aspect_ratio)
    provider_choice = (generator or settings.image_generator_provider or "auto").lower()

    # Determine provider execution
    gen_result: dict[str, Any]
    if mock or settings.mock_image_generation or provider_choice == "mock":
        gen_result = _generate_mock(
            prompt=prompt,
            style=style,
            colorway=colorway,
            pose=pose,
            aspect_ratio=aspect_ratio,
            text_overlay=text_overlay,
        )
    elif provider_choice == "openai":
        gen_result = await _generate_openai(prompt=prompt, size=dims)
    elif provider_choice == "replicate":
        gen_result = await _generate_replicate(prompt=prompt, aspect_ratio=ratio)
    else:  # "auto"
        if settings.openai_api_key:
            try:
                gen_result = await _generate_openai(prompt=prompt, size=dims)
            except Exception as exc:
                log.warning("OpenAI generation failed, falling back to mock: %s", exc)
                gen_result = _generate_mock(
                    prompt=prompt,
                    style=style,
                    colorway=colorway,
                    pose=pose,
                    aspect_ratio=aspect_ratio,
                    text_overlay=text_overlay,
                )
        elif settings.replicate_api_token:
            try:
                gen_result = await _generate_replicate(prompt=prompt, aspect_ratio=ratio)
            except Exception as exc:
                log.warning("Replicate generation failed, falling back to mock: %s", exc)
                gen_result = _generate_mock(
                    prompt=prompt,
                    style=style,
                    colorway=colorway,
                    pose=pose,
                    aspect_ratio=aspect_ratio,
                    text_overlay=text_overlay,
                )
        else:
            # Keyless local or test environment fallback
            gen_result = _generate_mock(
                prompt=prompt,
                style=style,
                colorway=colorway,
                pose=pose,
                aspect_ratio=aspect_ratio,
                text_overlay=text_overlay,
            )

    chosen_network = network or settings.revenue_network or "eip155:8453"

    return {
        "success": True,
        "product_id": PRODUCT_ID,
        "image_url": gen_result["image_url"],
        "prompt_used": prompt,
        "revised_prompt": gen_result.get("revised_prompt", prompt),
        "parameters": {
            "style": style,
            "colorway": colorway,
            "pose": pose,
            "aspect_ratio": dims,
            "custom_prompt": custom_prompt,
            "text_overlay": text_overlay,
        },
        "generator": gen_result.get("provider", "mock"),
        "model": gen_result.get("model", "merchforge-svg-engine-v1"),
        "commerce": {
            "product_id": PRODUCT_ID,
            "sku": SKU,
            "price_usd": PRICE_USD,
            "price_usdc": PRICE_USDC,
            "network": chosen_network,
            "license": LICENSE,
            "attribution": ATTRIBUTION,
        },
    }


def get_sample_poster() -> dict[str, Any]:
    """Provide a deterministic free sample poster payload for discovery and catalog previews."""
    sample_prompt = build_fusion_panda_prompt(
        style="cyberpunk_classic",
        colorway="neon_noir",
        pose="heroic_standing",
        aspect_ratio="1024x1792",
        text_overlay="CYBER PANDA 2099",
    )
    mock_gen = _generate_mock(
        prompt=sample_prompt,
        style="cyberpunk_classic",
        colorway="neon_noir",
        pose="heroic_standing",
        aspect_ratio="1024x1792",
        text_overlay="CYBER PANDA 2099",
    )
    return {
        "sample": True,
        "product_id": PRODUCT_ID,
        "image_url": mock_gen["image_url"],
        "prompt_used": sample_prompt,
        "revised_prompt": sample_prompt,
        "parameters": {
            "style": "cyberpunk_classic",
            "colorway": "neon_noir",
            "pose": "heroic_standing",
            "aspect_ratio": "1024x1792",
            "text_overlay": "CYBER PANDA 2099",
        },
        "generator": "mock",
        "commerce": {
            "product_id": PRODUCT_ID,
            "sku": SKU,
            "price_usd": PRICE_USD,
            "price_usdc": PRICE_USDC,
            "network": "eip155:8453",
            "license": LICENSE,
            "attribution": ATTRIBUTION,
        },
    }


# ---- x402 Seller Gate & Verification ---------------------------------------


def resource_url() -> str:
    """Canonical public URL for this paid poster resource."""
    return f"{settings.public_base_url.rstrip('/')}/poster/fusion-panda"


SAMPLE_PARAMETERS: dict[str, Any] = {
    "style": "cyberpunk_classic",
    "colorway": "neon_noir",
    "pose": "heroic_standing",
    "aspect_ratio": "1024x1792",
    "text_overlay": "CYBER PANDA 2099",
}

DISCOVERY_INPUT_EXAMPLE: dict[str, Any] = SAMPLE_PARAMETERS

DISCOVERY_OUTPUT_EXAMPLE: dict[str, Any] = {
    "success": True,
    "product_id": PRODUCT_ID,
    "image_url": "data:image/svg+xml;utf8,...",
    "prompt_used": "Masterpiece cyberpunk graphic art poster featuring an anthropomorphic cyber-panda warrior...",
    "parameters": SAMPLE_PARAMETERS,
    "generator": "openai",
    "commerce": {
        "product_id": PRODUCT_ID,
        "sku": SKU,
        "price_usd": PRICE_USD,
        "price_usdc": PRICE_USDC,
        "network": "eip155:8453",
        "license": LICENSE,
    },
}


def build_payment_required_header(
    network: str | None = None,
    price: str | None = None,
) -> str:
    """Build base64 x402 v2 PAYMENT-REQUIRED header for the poster generator endpoint."""
    from app import challenge_cache
    from app.models import BuildSellerRequirementsInput
    from app.x402_services import build_seller_requirements

    net = network or settings.revenue_network or "eip155:8453"
    cost = price or settings.fusion_panda_poster_price

    fp = challenge_cache.fingerprint(
        network=net,
        price=cost,
        resource=resource_url(),
        discoverable=settings.bazaar_discoverable,
        description=RESOURCE_DESCRIPTION,
        input_example=DISCOVERY_INPUT_EXAMPLE,
        output_example=DISCOVERY_OUTPUT_EXAMPLE,
        service_name=SERVICE_NAME,
        service_tags=SERVICE_TAGS,
    )

    def _build() -> str:
        return build_seller_requirements(
            BuildSellerRequirementsInput(
                network=net,
                price=cost,
                description=RESOURCE_DESCRIPTION,
                resource_url=resource_url(),
                mime_type="application/json",
                discovery_method="POST",
                discovery_input_example=DISCOVERY_INPUT_EXAMPLE,
                discovery_output_example=DISCOVERY_OUTPUT_EXAMPLE,
                service_name=SERVICE_NAME,
                service_tags=SERVICE_TAGS,
            )
        )["payment_required_header"]

    return challenge_cache.get_or_build("fusion-panda-poster", fp, _build)


def build_poster_challenge(
    price_usd: float = 0.49,
    network: str | None = None,
    resource_url_override: str | None = None,
) -> dict[str, Any]:
    """Build x402 seller challenge dictionary for the Fusion Panda poster product."""
    from app.models import BuildSellerRequirementsInput
    from app.x402_services import build_seller_requirements

    net = network or settings.revenue_network or "eip155:8453"
    cost = f"${price_usd:.2f}"
    res_url = resource_url_override or resource_url()

    return build_seller_requirements(
        BuildSellerRequirementsInput(
            network=net,
            price=cost,
            description=RESOURCE_DESCRIPTION,
            resource_url=res_url,
            mime_type="application/json",
            discovery_method="POST",
            discovery_input_example=DISCOVERY_INPUT_EXAMPLE,
            discovery_output_example=DISCOVERY_OUTPUT_EXAMPLE,
            service_name=SERVICE_NAME,
            service_tags=SERVICE_TAGS,
        )
    )


async def verify_and_settle(payment_signature: str, payment_required: str) -> dict[str, Any]:
    """Verify and settle an incoming x402 payment signature for the poster generator."""
    from app.models import VerifyPaymentInput
    from app.x402_services import _verify_and_settle_payment

    return await _verify_and_settle_payment(
        VerifyPaymentInput(
            payment_signature=payment_signature,
            payment_required=payment_required,
        )
    )
