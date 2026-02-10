import pytest

from asi.brain.protocol import ProtocolError, parse_model_output


def test_parse_valid_final() -> None:
    parsed = parse_model_output('{"type":"final","content":"ok"}')
    assert parsed["type"] == "final"


def test_parse_valid_tool_call() -> None:
    parsed = parse_model_output('{"type":"tool_call","name":"echo","args":{"text":"x"}}')
    assert parsed["type"] == "tool_call"


def test_parse_valid_tool_calls() -> None:
    parsed = parse_model_output(
        '{"type":"tool_calls","calls":[{"name":"echo","args":{"text":"a"}}]}'
    )
    assert parsed["type"] == "tool_calls"


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(ProtocolError):
        parse_model_output("{bad json")


def test_parse_missing_type_raises() -> None:
    with pytest.raises(ProtocolError):
        parse_model_output('{"content":"x"}')


def test_parse_unknown_type_raises() -> None:
    with pytest.raises(ProtocolError):
        parse_model_output('{"type":"unknown","content":"x"}')
