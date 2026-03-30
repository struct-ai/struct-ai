"""Tests for OpenAIMentorAdapter."""

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


def _make_mock_client(content: str | None) -> Any:
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
    from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter

    adapter: Any = OpenAIMentorAdapter.__new__(OpenAIMentorAdapter)
    adapter._client = _make_mock_client(content)
    return adapter


def describe_OpenAIMentorAdapter() -> None:
    def describe_suggest() -> None:
        def it_returns_valid_suggestion_for_well_formed_response() -> None:
            adapter = _make_adapter(json.dumps(_VALID_PAYLOAD))
            suggestion = adapter.suggest(
                "from struct_ai.adapters.parsers import PythonAstAdapter",
                RuleType.LAYER_VIOLATION,
            )
            assert suggestion.concept_name == "Layer Violation"
            assert "domain" in suggestion.educational_explanation.lower()
            assert suggestion.code_before == _VALID_PAYLOAD["code_before"]
            assert suggestion.documentation_links == []

        def it_raises_environment_error_when_api_key_missing(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.delenv("OPENAI_API_KEY", raising=False)
            from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter

            with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
                OpenAIMentorAdapter()

        def it_raises_when_response_content_is_empty() -> None:
            adapter = _make_adapter(None)
            with pytest.raises(AIMentorResponseError, match="empty response"):
                adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)

        def it_raises_when_choices_list_is_empty() -> None:
            mock_completion = MagicMock()
            mock_completion.choices = []
            mock_client: Any = MagicMock()
            mock_client.chat.completions.create.return_value = mock_completion

            from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter

            adapter: Any = OpenAIMentorAdapter.__new__(OpenAIMentorAdapter)
            adapter._client = mock_client

            with pytest.raises(AIMentorResponseError, match="no completion choices"):
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

    def describe_build_user_message() -> None:
        def it_embeds_snippet_and_rule_name() -> None:
            from struct_ai.adapters.ai.base_mentor_adapter import _build_user_message

            code = "import something_bad"
            rule = RuleType.LAYER_VIOLATION
            message = _build_user_message(code, rule)
            assert code in message
            assert rule.value in message
