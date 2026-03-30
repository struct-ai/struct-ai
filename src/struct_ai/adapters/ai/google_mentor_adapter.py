"""
Google (Gemini) implementation of AIMentorPort.

Requires the optional `google-generativeai` package:
    pip install "struct-ai[google]"

API key resolved via GOOGLE_API_KEY environment variable.
"""

import os
from typing import Any, Final

from struct_ai.adapters.ai.base_mentor_adapter import SYSTEM_PROMPT, BaseMentorAdapter
from struct_ai.core.exceptions.exceptions import AIMentorResponseError

_MODEL: Final[str] = "gemini-1.5-flash"


class GoogleMentorAdapter(BaseMentorAdapter):
    """
    Calls Google Gemini's GenerativeModel API.
    API key resolved via GOOGLE_API_KEY environment variable.
    Requires the optional `google-generativeai` package.
    """

    @property
    def provider_name(self) -> str:
        return "Google Gemini"

    def __init__(self, api_key: str | None = None) -> None:
        try:
            import google.generativeai as genai  # noqa: PLC0415
        except ImportError as error:
            raise ImportError(
                "The 'google-generativeai' package is required for GoogleMentorAdapter. "
                "Install it with: pip install 'struct-ai[google]'"
            ) from error

        resolved_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not resolved_key:
            raise EnvironmentError(
                "GOOGLE_API_KEY is not set. "
                "Provide it as an environment variable or pass it explicitly."
            )
        genai.configure(api_key=resolved_key)
        self._model: Any = genai.GenerativeModel(
            model_name=_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )

    def _call_api(self, user_message: str) -> str:
        response = self._model.generate_content(user_message)
        raw_content = getattr(response, "text", None)
        if not raw_content or not isinstance(raw_content, str):
            raise AIMentorResponseError(
                "Google Gemini returned an empty or non-text response.",
                raw_response=None,
            )
        return str(raw_content)
