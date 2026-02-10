from __future__ import annotations

import json
from typing import Any, TypedDict


class FinalResponse(TypedDict):
    type: str
    content: str


class ToolCall(TypedDict):
    name: str
    args: dict[str, Any]


class ToolCallResponse(TypedDict):
    type: str
    name: str
    args: dict[str, Any]


class ToolCallsResponse(TypedDict):
    type: str
    calls: list[ToolCall]


class ProtocolError(Exception):
    pass


def parse_model_output(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError("invalid_json") from exc

    if not isinstance(payload, dict):
        raise ProtocolError("root_must_be_object")

    kind = payload.get("type")
    if kind not in {"final", "tool_call", "tool_calls"}:
        raise ProtocolError("unknown_or_missing_type")

    if kind == "final":
        if not isinstance(payload.get("content"), str):
            raise ProtocolError("final_missing_content")
        return payload

    if kind == "tool_call":
        if not isinstance(payload.get("name"), str):
            raise ProtocolError("tool_call_missing_name")
        args = payload.get("args")
        if not isinstance(args, dict):
            raise ProtocolError("tool_call_args_must_be_object")
        return payload

    calls = payload.get("calls")
    if not isinstance(calls, list) or not calls:
        raise ProtocolError("tool_calls_missing_calls")
    for item in calls:
        if not isinstance(item, dict):
            raise ProtocolError("tool_calls_item_must_be_object")
        if not isinstance(item.get("name"), str):
            raise ProtocolError("tool_calls_item_missing_name")
        if not isinstance(item.get("args"), dict):
            raise ProtocolError("tool_calls_item_args_must_be_object")
    return payload
