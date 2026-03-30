"""
Anthropic (Claude) implementation of AIMentorPort.

Requires the optional `anthropic` package:
    pip install "struct-ai[anthropic]"

API key resolved via ANTHROPIC_API_KEY environment variable.
"""

import os
from typing import Any, Final

from struct_ai.adapters.ai.base_mentor_adapter import SYSTEM_PROMPT, BaseMentorAdapter
from struct_ai.core.exceptions.exceptions import AIMentorResponseError

_MODEL: Final[str] = "claude-3-5-sonnet-20241022"
_MAX_TOKENS: Final[int] = 1024


class AnthropicMentorAdapter(BaseMentorAdapter):
    """
    Calls Anthropic's Messages API.
    API key resolved via ANTHROPIC_API_KEY environment variable.
    Requires the optional `anthropic` package.
    """

    @property
    def provider_name(self) -> str:
        return "Anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        try:
            import anthropic as anthropic_sdk  # noqa: PLC0415
        except ImportError as error:
            raise ImportError(
                "The 'anthropic' package is required for AnthropicMentorAdapter. "
                "Install it with: pip install 'struct-ai[anthropic]'"
            ) from error

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Provide it as an environment variable or pass it explicitly."
            )
        self._client: Any = anthropic_sdk.Anthropic(api_key=resolved_key)

    def _call_api(self, user_message: str) -> str:
        response = self._client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        if not response.content:
            raise AIMentorResponseError(
                "Anthropic returned an empty response (no content blocks).",
                raw_response=None,
            )
        # TextBlock carries a `text` attribute; guard against future block types.
        raw_content = getattr(response.content[0], "text", None)
        if not raw_content or not isinstance(raw_content, str):
            raise AIMentorResponseError(
                "Anthropic returned an empty or non-text response.",
                raw_response=None,
            )
        return str(raw_content)
