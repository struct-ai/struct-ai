"""Tests for the AIMentorAdapterFactory (build_mentor_adapter)."""

import pytest

from struct_ai.adapters.ai.mentor_adapter_factory import build_mentor_adapter


def describe_build_mentor_adapter() -> None:
    def describe_explicit_provider() -> None:
        def it_returns_openai_adapter_when_provider_is_openai(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
            from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter

            adapter = build_mentor_adapter("openai")
            assert isinstance(adapter, OpenAIMentorAdapter)

        def it_returns_ollama_adapter_when_provider_is_ollama() -> None:
            from struct_ai.adapters.ai.ollama_mentor_adapter import OllamaMentorAdapter

            adapter = build_mentor_adapter("ollama")
            assert isinstance(adapter, OllamaMentorAdapter)

        def it_raises_environment_error_for_anthropic_without_key(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
            # ImportError is raised when the optional SDK is not installed;
            # EnvironmentError is raised when the SDK is present but key is missing.
            with pytest.raises((EnvironmentError, ImportError)):
                build_mentor_adapter("anthropic")

        def it_raises_environment_error_for_google_without_key(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
            with pytest.raises((EnvironmentError, ImportError)):
                build_mentor_adapter("google")

        def it_raises_environment_error_for_mistral_without_key(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
            with pytest.raises((EnvironmentError, ImportError)):
                build_mentor_adapter("mistral")

    def describe_auto_detection() -> None:
        def it_detects_openai_from_env(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
            monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
            monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
            monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
            monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

            from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter

            adapter = build_mentor_adapter(None)
            assert isinstance(adapter, OpenAIMentorAdapter)

        def it_detects_ollama_when_base_url_is_set_and_openai_is_absent(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
            monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
            monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
            monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
            monkeypatch.delenv("OPENAI_API_KEY", raising=False)

            from struct_ai.adapters.ai.ollama_mentor_adapter import OllamaMentorAdapter

            adapter = build_mentor_adapter(None)
            assert isinstance(adapter, OllamaMentorAdapter)

        def it_raises_when_no_env_var_is_set(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
            monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
            monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
            monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
            monkeypatch.delenv("OPENAI_API_KEY", raising=False)

            with pytest.raises(EnvironmentError, match="No LLM provider"):
                build_mentor_adapter(None)
