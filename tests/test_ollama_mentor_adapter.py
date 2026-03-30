"""Tests for OllamaMentorAdapter."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

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

_VALID_OLLAMA_RESPONSE = {
    "message": {"content": json.dumps(_VALID_PAYLOAD)},
}


def _make_adapter(
    base_url: str = "http://localhost:11434",
    model: str = "llama3",
) -> Any:
    from struct_ai.adapters.ai.ollama_mentor_adapter import OllamaMentorAdapter

    return OllamaMentorAdapter(base_url=base_url, model=model)


def _mock_urlopen(response_body: bytes) -> Any:
    mock_http_response = MagicMock()
    mock_http_response.__enter__ = MagicMock(return_value=mock_http_response)
    mock_http_response.__exit__ = MagicMock(return_value=False)
    mock_http_response.read.return_value = response_body
    return MagicMock(return_value=mock_http_response)


def describe_OllamaMentorAdapter() -> None:
    def describe_init() -> None:
        def it_uses_default_base_url_and_model(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
            monkeypatch.delenv("OLLAMA_MODEL", raising=False)
            from struct_ai.adapters.ai.ollama_mentor_adapter import OllamaMentorAdapter

            instance: Any = OllamaMentorAdapter()
            assert instance._base_url == "http://localhost:11434"
            assert instance._model == "llama3"

        def it_uses_env_vars_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
            monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:9999")
            monkeypatch.setenv("OLLAMA_MODEL", "mistral")
            from struct_ai.adapters.ai.ollama_mentor_adapter import OllamaMentorAdapter

            instance: Any = OllamaMentorAdapter()
            assert instance._base_url == "http://custom:9999"
            assert instance._model == "mistral"

    def describe_suggest() -> None:
        def it_returns_valid_suggestion_for_well_formed_response() -> None:
            adapter: Any = _make_adapter()
            raw = json.dumps(_VALID_OLLAMA_RESPONSE).encode("utf-8")
            with patch("urllib.request.urlopen", _mock_urlopen(raw)):
                suggestion = adapter.suggest(
                    "from struct_ai.adapters.parsers import PythonAstAdapter",
                    RuleType.LAYER_VIOLATION,
                )
            assert suggestion.concept_name == "Layer Violation"
            assert suggestion.documentation_links == []

        def it_raises_when_server_is_unreachable() -> None:
            import urllib.error

            adapter: Any = _make_adapter()
            with patch(
                "urllib.request.urlopen",
                side_effect=urllib.error.URLError("Connection refused"),
            ):
                with pytest.raises(AIMentorResponseError, match="unreachable"):
                    adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)

        def it_raises_when_server_returns_non_json() -> None:
            adapter: Any = _make_adapter()
            with patch("urllib.request.urlopen", _mock_urlopen(b"not json")):
                with pytest.raises(AIMentorResponseError, match="non-JSON"):
                    adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)

        def it_raises_when_message_content_is_missing() -> None:
            adapter: Any = _make_adapter()
            bad_body = json.dumps({"message": {}}).encode("utf-8")
            with patch("urllib.request.urlopen", _mock_urlopen(bad_body)):
                with pytest.raises(AIMentorResponseError, match="empty or malformed"):
                    adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)

        def it_raises_when_model_response_is_not_valid_json() -> None:
            adapter: Any = _make_adapter()
            body = json.dumps({"message": {"content": "not json"}}).encode("utf-8")
            with patch("urllib.request.urlopen", _mock_urlopen(body)):
                with pytest.raises(AIMentorResponseError, match="not valid JSON"):
                    adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)

        def it_raises_when_model_response_missing_required_fields() -> None:
            adapter: Any = _make_adapter()
            incomplete = json.dumps({"concept_name": "x"})
            body = json.dumps({"message": {"content": incomplete}}).encode("utf-8")
            with patch("urllib.request.urlopen", _mock_urlopen(body)):
                with pytest.raises(AIMentorResponseError, match="Suggestion schema"):
                    adapter.suggest("x = 1", RuleType.LAYER_VIOLATION)
