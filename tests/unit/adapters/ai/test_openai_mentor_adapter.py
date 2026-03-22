"""
Unit tests for OpenAIMentorAdapter.

Strategy: mock the OpenAI client entirely — no real HTTP calls.
Uses ``unittest.mock`` (stdlib), not ``pytest-mock``.
We test:
  - Happy path: well-formed JSON → valid Suggestion returned.
  - Missing OPENAI_API_KEY → EnvironmentError raised.
  - OpenAI returns empty content → AIMentorResponseError raised.
  - OpenAI returns no choices → AIMentorResponseError raised.
  - OpenAI returns invalid JSON → AIMentorResponseError raised.
  - OpenAI returns JSON with missing Suggestion fields → AIMentorResponseError raised.
  - User message embeds the code snippet and rule name correctly.
"""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.exceptions.exceptions import AIMentorResponseError

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

_VALID_PAYLOAD = {
    "concept_name": "Layer Violation",
    "educational_explanation": "The domain layer must not depend on infrastructure.",
    "code_before": "from struct_ai.adapters.parsers import PythonAstAdapter",
    "code_after": "from struct_ai.core.interfaces.outputs.code_parser_port import CodeParserPort",
    "documentation_links": [],
}


def _make_mock_client(content: str | None) -> Any:
    """
    Build a MagicMock that mimics the minimal openai.OpenAI interface used by
    the adapter (_client.chat.completions.create returns a completion-like object).
    """
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client: Any = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion
    return mock_client


def _make_adapter(content: str | None) -> Any:
    """Instantiate OpenAIMentorAdapter without constructor (bypasses API key check)."""
    from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter

    adapter: Any = OpenAIMentorAdapter.__new__(OpenAIMentorAdapter)
    adapter._client = _make_mock_client(content)
    return adapter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_suggest_returns_valid_suggestion() -> None:
    """Well-formed JSON response maps to a frozen Suggestion."""
    adapter = _make_adapter(json.dumps(_VALID_PAYLOAD))

    suggestion = adapter.suggest(
        "from struct_ai.adapters.parsers import PythonAstAdapter",
        RuleType.LAYER_VIOLATION,
    )

    assert suggestion.concept_name == "Layer Violation"
    assert "domain" in suggestion.educational_explanation.lower()
    assert suggestion.code_before == _VALID_PAYLOAD["code_before"]
    assert suggestion.code_after == _VALID_PAYLOAD["code_after"]
    assert suggestion.documentation_links == []


def test_suggest_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing OPENAI_API_KEY raises EnvironmentError on construction."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter

    with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
        OpenAIMentorAdapter()


def test_suggest_raises_when_openai_returns_empty_content() -> None:
    """Empty content from the API raises AIMentorResponseError."""
    adapter = _make_adapter(None)

    with pytest.raises(AIMentorResponseError, match="empty response"):
        adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)


def test_suggest_raises_when_openai_returns_no_choices() -> None:
    """An empty choices list raises AIMentorResponseError with raw_response None."""
    mock_completion = MagicMock()
    mock_completion.choices = []
    mock_client: Any = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter

    adapter: Any = OpenAIMentorAdapter.__new__(OpenAIMentorAdapter)
    adapter._client = mock_client

    with pytest.raises(
        AIMentorResponseError, match="no completion choices"
    ) as exc_info:
        adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)

    assert exc_info.value.raw_response is None


def test_suggest_raises_when_response_is_not_json() -> None:
    """Non-JSON response raises AIMentorResponseError."""
    adapter = _make_adapter("not json at all")

    with pytest.raises(AIMentorResponseError, match="not valid JSON"):
        adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)


def test_suggest_raises_when_response_missing_required_fields() -> None:
    """JSON missing required Suggestion fields raises AIMentorResponseError."""
    incomplete = {"concept_name": "Layer Violation"}  # missing other required fields
    adapter = _make_adapter(json.dumps(incomplete))

    with pytest.raises(AIMentorResponseError, match="Suggestion schema"):
        adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)


def test_user_message_embeds_snippet_and_rule() -> None:
    """The user message sent to OpenAI contains the code snippet and rule name."""
    from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter

    adapter: Any = OpenAIMentorAdapter.__new__(OpenAIMentorAdapter)
    code = "import something_bad"
    rule = RuleType.LAYER_VIOLATION

    message = adapter._build_user_message(code, rule)

    assert code in message
    assert rule.value in message
