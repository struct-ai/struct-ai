"""Tests for AnthropicMentorAdapter."""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.exceptions.exceptions import AIMentorResponseError

_VALID_PAYLOAD = {
    "concept_name": "Layer Violation",
    "educational_explanation": "The domain layer must not depend on infrastructure.",
    "code_before": "from struct_ai.adapters.parsers import PythonAstAdapter",
    "code_after": "from struct_ai.core.interfaces.outputs.code_parser_port import CodeParserPort",
    "documentation_links": [],
}


def _make_mock_client(text_content: str | None) -> Any:
    mock_block = MagicMock()
    mock_block.text = text_content
    mock_response = MagicMock()
    mock_response.content = [mock_block] if text_content is not None else []
    mock_client: Any = MagicMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


def _make_adapter(text_content: str | None) -> Any:
    from struct_ai.adapters.ai.anthropic_mentor_adapter import AnthropicMentorAdapter

    adapter: Any = AnthropicMentorAdapter.__new__(AnthropicMentorAdapter)
    adapter._client = _make_mock_client(text_content)
    return adapter


def describe_AnthropicMentorAdapter() -> None:
    def describe_suggest() -> None:
        def it_returns_valid_suggestion_for_well_formed_response() -> None:
            adapter = _make_adapter(json.dumps(_VALID_PAYLOAD))
            suggestion = adapter.suggest(
                "from struct_ai.adapters.parsers import PythonAstAdapter",
                RuleType.LAYER_VIOLATION,
            )
            assert suggestion.concept_name == "Layer Violation"
            assert "domain" in suggestion.educational_explanation.lower()
            assert suggestion.documentation_links == []

        def it_raises_environment_error_when_api_key_missing(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
            try:
                from struct_ai.adapters.ai.anthropic_mentor_adapter import (
                    AnthropicMentorAdapter,
                )

                with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
                    AnthropicMentorAdapter()
            except ImportError:
                pytest.skip("anthropic package not installed")

        def it_raises_when_response_content_is_empty() -> None:
            adapter = _make_adapter(None)
            with pytest.raises(AIMentorResponseError, match="empty"):
                adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)

        def it_raises_when_response_is_not_json() -> None:
            adapter = _make_adapter("not json at all")
            with pytest.raises(AIMentorResponseError, match="not valid JSON"):
                adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)

        def it_raises_when_response_is_missing_required_fields() -> None:
            incomplete = {"concept_name": "Layer Violation"}
            adapter = _make_adapter(json.dumps(incomplete))
            with pytest.raises(AIMentorResponseError, match="Suggestion schema"):
                adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)
