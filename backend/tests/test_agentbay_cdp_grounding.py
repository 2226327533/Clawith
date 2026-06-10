from __future__ import annotations

import sys
import types


fake_agentbay = types.ModuleType("agentbay")
fake_agentbay.AgentBay = object
fake_agentbay.CreateSessionParams = object
sys.modules.setdefault("agentbay", fake_agentbay)

from app.services.agentbay_client import (  # noqa: E402
    _normalized_box_center_to_pixel,
    _parse_grounding_json,
)


def test_parse_grounding_json_accepts_fenced_json():
    data = _parse_grounding_json(
        """```json
        {"target": "Search box", "box_2d": [100, 200, 300, 600], "confidence": 0.9}
        ```"""
    )

    assert data["target"] == "Search box"
    assert data["box_2d"] == [100, 200, 300, 600]


def test_normalized_box_center_to_pixel_uses_gemini_yxyx_order():
    ymin, xmin, ymax, xmax, x, y = _normalized_box_center_to_pixel(
        [100, 200, 300, 600],
        width=1920,
        height=1080,
    )

    assert (ymin, xmin, ymax, xmax) == (100, 200, 300, 600)
    assert x == 768
    assert y == 216


def test_normalized_box_center_to_pixel_clamps_to_image_bounds():
    *_, x, y = _normalized_box_center_to_pixel(
        [1500, 1500, 1700, 1700],
        width=100,
        height=50,
    )

    assert x == 99
    assert y == 49
