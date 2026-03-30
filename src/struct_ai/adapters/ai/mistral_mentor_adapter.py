"""
Mistral AI implementation of AIMentorPort.

Requires the optional `mistralai` package:
    pip install "struct-ai[mistral]"

API key resolved via MISTRAL_API_KEY environment variable.
"""

import os
from typing import Any, Final

from struct_ai.adapters.ai.base_mentor_adapter import SYSTEM_PROMPT, BaseMentorAdapter
from struct_ai.core.exceptions.exceptions import AIMentorResponseError

_MODEL: Final[str] = "mistral-large-latest"


class MistralMentorAdapter(BaseMentorAdapter):
    """
    Calls Mistral AI's chat API.
    API key resolved via MISTRAL_API_KEY environment variable.
    Requires the optional `mistralai` package.
    """

    @property
    def provider_name(self) -> str:
        return "Mistral"

    def __init__(self, api_key: str | None = None) -> None:
        try:
            from mistralai import Mistral  # noqa: PLC0415
        except ImportError as error:
            raise ImportError(
                "The 'mistralai' package is required for MistralMentorAdapter. "
                "Install it with: pip install 'struct-ai[mistral]'"
            ) from error

        resolved_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not resolved_key:
            raise EnvironmentError(
                "MISTRAL_API_KEY is not set. "
                "Provide it as an environment variable or pass it explicitly."
            )
        self._client: Any = Mistral(api_key=resolved_key)

    def _call_api(self, user_message: str) -> str:
        response = self._client.chat.complete(
            model=_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        choices = getattr(response, "choices", None)
        if not choices:
            raise AIMentorResponseError(
                "Mistral returned no completion choices.",
                raw_response=None,
            )
        message = getattr(choices[0], "message", None)
        if message is None:
            raise AIMentorResponseError(
                "Mistral completion has no message.",
                raw_response=None,
            )
        raw_content = getattr(message, "content", None)
        if not raw_content or not isinstance(raw_content, str):
            raise AIMentorResponseError(
                "Mistral returned an empty or non-text response.",
                raw_response=None,
            )
        return str(raw_content)
