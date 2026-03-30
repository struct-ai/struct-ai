"""OpenAI-backed implementation of AIMentorPort."""

import os
from typing import Final

from openai import OpenAI

from struct_ai.adapters.ai.base_mentor_adapter import SYSTEM_PROMPT, BaseMentorAdapter
from struct_ai.core.exceptions.exceptions import AIMentorResponseError

_MODEL: Final[str] = "gpt-4o"
_TEMPERATURE: Final[float] = 0.2


class OpenAIMentorAdapter(BaseMentorAdapter):
    """
    Calls OpenAI's Chat Completions API in JSON mode.
    API key resolved via OPENAI_API_KEY environment variable.
    """

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Provide it as an environment variable or pass it explicitly."
            )
        self._client = OpenAI(api_key=resolved_key)

    def _call_api(self, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=_MODEL,
            temperature=_TEMPERATURE,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        choices = getattr(response, "choices", None)
        if not choices:
            raise AIMentorResponseError(
                "OpenAI returned no completion choices.",
                raw_response=None,
            )
        message = getattr(choices[0], "message", None)
        if message is None:
            raise AIMentorResponseError(
                "OpenAI completion has no message.",
                raw_response=None,
            )
        content = getattr(message, "content", None)
        if content is None:
            raise AIMentorResponseError(
                "OpenAI returned an empty response.",
                raw_response=None,
            )
        if not isinstance(content, str):
            raise AIMentorResponseError(
                "OpenAI completion content is not a string.",
                raw_response=None,
            )
        return content
