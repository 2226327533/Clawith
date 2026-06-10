from __future__ import annotations

from app.services.llm.caller import _split_tool_result_and_vision_message


def test_screenshot_vision_is_sent_as_user_message_not_tool_content():
    tool_text, user_message = _split_tool_result_and_vision_message(
        "agentbay_browser_screenshot",
        "raw [ImageID: abc]",
        [
            {"type": "text", "text": "Internal screenshot captured for analysis."},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/test"}},
        ],
    )

    assert tool_text == "Internal screenshot captured for analysis."
    assert user_message is not None
    assert user_message.role == "user"
    assert user_message.content[0]["type"] == "text"
    assert user_message.content[1]["type"] == "image_url"
