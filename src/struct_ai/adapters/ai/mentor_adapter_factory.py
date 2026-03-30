"""
Factory function for AIMentorPort adapters.

Resolution order (highest → lowest priority):
1. Explicit ``provider`` argument (from CLI flag or .struct-ia.yaml)
2. Environment-variable auto-detection (first matching key wins):
   ANTHROPIC_API_KEY → anthropic
   GOOGLE_API_KEY    → google
   MISTRAL_API_KEY   → mistral
   OLLAMA_BASE_URL   → ollama  (server is assumed to be running)
   OPENAI_API_KEY    → openai  (default fallback)
3. Raises EnvironmentError when no provider can be resolved.

Each provider SDK is imported lazily so missing optional packages only
raise at instantiation time, not at import time.
"""

import os

from struct_ai.core.entities.config import ProviderSlug
from struct_ai.core.interfaces.ai_mentor_port import AIMentorPort

_ENV_VAR_TO_PROVIDER: tuple[tuple[str, ProviderSlug], ...] = (
    ("ANTHROPIC_API_KEY", "anthropic"),
    ("GOOGLE_API_KEY", "google"),
    ("MISTRAL_API_KEY", "mistral"),
    ("OLLAMA_BASE_URL", "ollama"),
    ("OPENAI_API_KEY", "openai"),
)


def build_mentor_adapter(provider: ProviderSlug | None) -> AIMentorPort:
    """
    Instantiate and return the concrete AIMentorPort implementation for the
    requested provider.

    Args:
        provider: Provider slug from config/CLI, or None to trigger auto-detection.

    Returns:
        A fully initialised AIMentorPort implementation.

    Raises:
        EnvironmentError: When ``provider`` is None and no API key / server URL
            is found in the environment, or when the explicit provider's
            required environment variable is missing.
        ImportError: When the requested provider's optional SDK is not installed.
    """
    resolved_provider = provider or _detect_provider_from_environment()
    return _instantiate(resolved_provider)


def _detect_provider_from_environment() -> ProviderSlug:
    """
    Scan environment variables in priority order and return the first matching
    provider slug.

    Raises:
        EnvironmentError: When no known API key or server URL is present.
    """
    for env_var, provider_slug in _ENV_VAR_TO_PROVIDER:
        if os.environ.get(env_var):
            return provider_slug

    available = ", ".join(env for env, _ in _ENV_VAR_TO_PROVIDER)
    raise EnvironmentError(
        "No LLM provider could be auto-detected. "
        "Set one of the following environment variables: "
        f"{available}. "
        "Alternatively, specify a provider in .struct-ia.yaml under the 'provider' key "
        "or via the --provider CLI flag."
    )


def _instantiate(provider: ProviderSlug) -> AIMentorPort:
    """Instantiate the adapter for the given provider slug."""
    if provider == "openai":
        from struct_ai.adapters.ai.openai_mentor_adapter import (  # noqa: PLC0415
            OpenAIMentorAdapter,
        )

        return OpenAIMentorAdapter()

    if provider == "anthropic":
        from struct_ai.adapters.ai.anthropic_mentor_adapter import (  # noqa: PLC0415
            AnthropicMentorAdapter,
        )

        return AnthropicMentorAdapter()

    if provider == "google":
        from struct_ai.adapters.ai.google_mentor_adapter import (  # noqa: PLC0415
            GoogleMentorAdapter,
        )

        return GoogleMentorAdapter()

    if provider == "mistral":
        from struct_ai.adapters.ai.mistral_mentor_adapter import (  # noqa: PLC0415
            MistralMentorAdapter,
        )

        return MistralMentorAdapter()

    if provider == "ollama":
        from struct_ai.adapters.ai.ollama_mentor_adapter import (  # noqa: PLC0415
            OllamaMentorAdapter,
        )

        return OllamaMentorAdapter()

    # This branch is unreachable when ProviderSlug is kept in sync with the
    # Literal type, but kept as an explicit guard against future drift.
    raise ValueError(f"Unknown provider slug: '{provider}'")
