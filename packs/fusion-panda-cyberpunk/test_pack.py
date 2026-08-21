"""Unit tests for Fusion Panda Cyberpunk Poster Prompt Pack Engine."""

from __future__ import annotations

import json
import urllib.parse
from unittest.mock import patch

import httpx
import pytest
import respx

from app.config import settings
from app.fusion_panda import (
    COLORWAY_PRESETS,
    POSE_PRESETS,
    PRICE_USDC,
    PRODUCT_ID,
    SKU,
    STYLE_PRESETS,
    ImageGenerationError,
    _generate_mock,
    _generate_openai,
    _generate_replicate,
    build_fusion_panda_prompt,
    build_payment_required_header,
    generate_poster,
    get_sample_poster,
    normalize_aspect_ratio,
)


def test_preset_definitions_complete():
    """Verify all 5 styles, 5 colorways, and 5 poses are defined."""
    assert len(STYLE_PRESETS) == 5
    assert set(STYLE_PRESETS.keys()) == {
        "cyberpunk_classic",
        "synthwave_retro",
        "techwear_tactical",
        "mecha_fusion",
        "neo_tokyo_ink",
    }

    assert len(COLORWAY_PRESETS) == 5
    assert set(COLORWAY_PRESETS.keys()) == {
        "neon_noir",
        "acid_hazard",
        "vapor_sunset",
        "obsidian_gold",
        "hyper_violet",
    }

    assert len(POSE_PRESETS) == 5
    assert set(POSE_PRESETS.keys()) == {
        "heroic_standing",
        "action_leap",
        "hacker_crouch",
        "street_portrait",
        "meditating_zen",
    }


def test_normalize_aspect_ratio():
    assert normalize_aspect_ratio("1024x1792") == ("1024x1792", "9:16")
    assert normalize_aspect_ratio("9:16") == ("1024x1792", "9:16")
    assert normalize_aspect_ratio("1024x1024") == ("1024x1024", "1:1")
    assert normalize_aspect_ratio("1:1") == ("1024x1024", "1:1")
    assert normalize_aspect_ratio("1792x1024") == ("1792x1024", "16:9")
    assert normalize_aspect_ratio("16:9") == ("1792x1024", "16:9")
    assert normalize_aspect_ratio("custom") == ("1024x1792", "9:16")


def test_build_fusion_panda_prompt_default():
    prompt = build_fusion_panda_prompt()
    assert "anthropomorphic cyber-panda warrior" in prompt
    assert "heroic power stance" in prompt
    assert "Gritty neon metropolis" in prompt
    assert "Electric cyan" in prompt


@pytest.mark.parametrize("style", list(STYLE_PRESETS.keys()))
@pytest.mark.parametrize("colorway", list(COLORWAY_PRESETS.keys()))
@pytest.mark.parametrize("pose", list(POSE_PRESETS.keys()))
def test_build_fusion_panda_prompt_combinations(style: str, colorway: str, pose: str):
    prompt = build_fusion_panda_prompt(style=style, colorway=colorway, pose=pose)
    assert style.replace("_", " ") in prompt or STYLE_PRESETS[style][:20] in prompt
    assert POSE_PRESETS[pose][:20] in prompt


def test_build_fusion_panda_prompt_custom_text_and_details():
    prompt = build_fusion_panda_prompt(
        style="synthwave_retro",
        colorway="vapor_sunset",
        pose="action_leap",
        custom_prompt="Holding a neon glowing dragon orb",
        text_overlay="CYBER PANDA 2099",
    )
    assert 'Poster Typography: Distinctive futuristic cyberpunk title typography displaying "CYBER PANDA 2099"' in prompt
    assert "Custom Aesthetic Detail: Holding a neon glowing dragon orb." in prompt


def test_build_fusion_panda_prompt_invalid_inputs():
    with pytest.raises(ValueError, match="Unknown style 'invalid_style'"):
        build_fusion_panda_prompt(style="invalid_style")

    with pytest.raises(ValueError, match="Unknown colorway 'invalid_colorway'"):
        build_fusion_panda_prompt(colorway="invalid_colorway")

    with pytest.raises(ValueError, match="Unknown pose 'invalid_pose'"):
        build_fusion_panda_prompt(pose="invalid_pose")


def test_generate_mock_output():
    res = _generate_mock(
        prompt="Test prompt",
        style="cyberpunk_classic",
        colorway="neon_noir",
        pose="heroic_standing",
        aspect_ratio="1024x1792",
        text_overlay="TEST POSTER",
    )
    assert res["provider"] == "mock"
    assert res["image_url"].startswith("data:image/svg+xml;utf8,")
    # Decode SVG and verify elements
    svg_str = urllib.parse.unquote(res["image_url"].split(",", 1)[1])
    assert "<svg" in svg_str
    assert "TEST POSTER" in svg_str
    assert "MERCHFORGE-PROMPT-PACK-V1" in svg_str
    assert "MF-FUSION-PANDA-POSTER-V1" in svg_str


@pytest.mark.asyncio
async def test_generate_poster_mock_mode():
    res = await generate_poster(
        style="mecha_fusion",
        colorway="acid_hazard",
        pose="hacker_crouch",
        mock=True,
    )
    assert res["success"] is True
    assert res["product_id"] == PRODUCT_ID
    assert res["commerce"]["sku"] == SKU
    assert res["commerce"]["price_usdc"] == PRICE_USDC
    assert res["parameters"]["style"] == "mecha_fusion"
    assert res["parameters"]["colorway"] == "acid_hazard"
    assert res["parameters"]["pose"] == "hacker_crouch"
    assert res["image_url"].startswith("data:image/svg+xml;utf8,")


@pytest.mark.asyncio
async def test_generate_openai_success():
    fake_url = "https://oaidalleapiprodscus.blob.core.windows.net/test-image.png"
    fake_revised = "Revised cyber panda prompt"

    with respx.mock(base_url="https://api.openai.com") as respx_mock:
        respx_mock.post("/v1/images/generations").respond(
            status_code=200,
            json={
                "created": 1720000000,
                "data": [{"url": fake_url, "revised_prompt": fake_revised}],
            },
        )

        res = await _generate_openai("prompt", size="1024x1792", api_key="sk-test-openai")
        assert res["image_url"] == fake_url
        assert res["revised_prompt"] == fake_revised
        assert res["provider"] == "openai"


@pytest.mark.asyncio
async def test_generate_openai_errors():
    with respx.mock(base_url="https://api.openai.com") as respx_mock:
        # 401
        respx_mock.post("/v1/images/generations").respond(
            status_code=401,
            json={"error": {"message": "Invalid API key"}},
        )
        with pytest.raises(ImageGenerationError) as exc_info:
            await _generate_openai("prompt", api_key="sk-invalid")
        assert exc_info.value.code == "invalid_api_key"

    with respx.mock(base_url="https://api.openai.com") as respx_mock:
        # 429
        respx_mock.post("/v1/images/generations").respond(
            status_code=429,
            json={"error": {"message": "Rate limit exceeded"}},
        )
        with pytest.raises(ImageGenerationError) as exc_info:
            await _generate_openai("prompt", api_key="sk-test")
        assert exc_info.value.code == "rate_limit_exceeded"

    with respx.mock(base_url="https://api.openai.com") as respx_mock:
        # 400 safety
        respx_mock.post("/v1/images/generations").respond(
            status_code=400,
            json={"error": {"message": "Your request was rejected due to safety policy"}},
        )
        with pytest.raises(ImageGenerationError) as exc_info:
            await _generate_openai("prompt", api_key="sk-test")
        assert exc_info.value.code == "prompt_policy_violation"


@pytest.mark.asyncio
async def test_generate_replicate_success():
    fake_out = ["https://replicate.delivery/pbxt/test.webp"]

    with respx.mock(base_url="https://api.replicate.com") as respx_mock:
        respx_mock.post("/v1/models/black-forest-labs/flux-schnell/predictions").respond(
            status_code=201,
            json={"status": "succeeded", "output": fake_out},
        )

        res = await _generate_replicate("prompt", aspect_ratio="9:16", api_token="r8_test")
        assert res["image_url"] == fake_out[0]
        assert res["provider"] == "replicate"


def test_get_sample_poster():
    sample = get_sample_poster()
    assert sample["sample"] is True
    assert sample["product_id"] == PRODUCT_ID
    assert sample["commerce"]["sku"] == SKU
    assert sample["commerce"]["price_usdc"] == 0.49
    assert "image_url" in sample


def test_build_payment_required_header(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "x402_pay_to_address", "0xTestPayTo00000000000000000000000001")
    header = build_payment_required_header(network="eip155:8453")
    assert isinstance(header, str)
    assert len(header) > 20


def test_build_poster_challenge(monkeypatch: pytest.MonkeyPatch):
    from app.fusion_panda import build_poster_challenge

    monkeypatch.setattr(settings, "x402_pay_to_address", "0xTestPayTo00000000000000000000000001")
    challenge = build_poster_challenge(price_usd=0.49, network="eip155:8453")
    assert challenge["price"] == "$0.49"
    assert challenge["network"] == "eip155:8453"
    assert "payment_required_header" in challenge

