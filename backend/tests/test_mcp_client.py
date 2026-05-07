import pytest

from app.services.mcp_client import MCPClient


@pytest.mark.asyncio
async def test_detect_and_request_reports_both_transport_errors(monkeypatch):
    client = MCPClient("https://example.invalid/mcp")

    async def fail_streamable(method, params=None):
        raise RuntimeError("streamable transport refused")

    async def fail_sse(method, params=None):
        raise RuntimeError("sse endpoint missing")

    monkeypatch.setattr(client, "_streamable_request", fail_streamable)
    monkeypatch.setattr(client, "_sse_request", fail_sse)

    with pytest.raises(Exception) as exc_info:
        await client._detect_and_request("tools/list")

    message = str(exc_info.value)
    assert message == (
        "Both transports failed. "
        "Streamable HTTP: streamable transport refused; "
        "SSE: sse endpoint missing"
    )
    assert client._transport is None
