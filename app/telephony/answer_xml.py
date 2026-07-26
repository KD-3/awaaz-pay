"""Generates the XML response for Vobiz's answer_url webhook (§5.2 equivalent
of Twilio's <Connect><Stream> TwiML), connecting the inbound call to our
`/stream` websocket as bidirectional 8kHz mulaw - matching Sarvam's
telephony-tuned format on both legs (§6)."""
from __future__ import annotations


def build_stream_answer_xml(stream_ws_url: str, status_callback_url: str | None = None) -> str:
    status_attr = f'\n        statusCallbackUrl="{status_callback_url}"' if status_callback_url else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        "    <Stream\n"
        '        bidirectional="true"\n'
        '        keepCallAlive="true"\n'
        '        contentType="audio/x-mulaw;rate=8000"'
        f"{status_attr}>\n"
        f"        {stream_ws_url}\n"
        "    </Stream>\n"
        "</Response>\n"
    )
