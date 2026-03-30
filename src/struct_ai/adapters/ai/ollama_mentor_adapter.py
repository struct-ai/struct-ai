"""
Ollama (local / self-hosted) implementation of AIMentorPort.

No extra dependencies — uses the standard library `urllib` to call the
Ollama REST API.

Configuration:
    OLLAMA_BASE_URL  Base URL of the Ollama server (default: http://localhost:11434)
    OLLAMA_MODEL     Model to use              (default: llama3)
"""

import json
import os
import urllib.error
import urllib.request
from typing import Final

from struct_ai.adapters.ai.base_mentor_adapter import SYSTEM_PROMPT, BaseMentorAdapter
from struct_ai.core.exceptions.exceptions import AIMentorResponseError

_DEFAULT_BASE_URL: Final[str] = "http://localhost:11434"
_DEFAULT_MODEL: Final[str] = "llama3"
_REQUEST_TIMEOUT_SECONDS: Final[int] = 120


class OllamaMentorAdapter(BaseMentorAdapter):
    """
    Calls a locally running Ollama server via its REST API.
    No external SDK — communicates over HTTP using the standard library.
    Server URL and model are resolved from environment variables with sane defaults.
    """

    @property
    def provider_name(self) -> str:
        return "Ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url: str = (
            base_url or os.environ.get("OLLAMA_BASE_URL") or _DEFAULT_BASE_URL
        ).rstrip("/")
        self._model: str = model or os.environ.get("OLLAMA_MODEL") or _DEFAULT_MODEL

    def _call_api(self, user_message: str) -> str:
        endpoint = f"{self._base_url}/api/chat"
        body = json.dumps(
            {
                "model": self._model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=_REQUEST_TIMEOUT_SECONDS
            ) as http_response:
                raw_body = http_response.read().decode("utf-8")
        except urllib.error.URLError as error:
            raise AIMentorResponseError(
                f"Ollama server unreachable at {endpoint}: {error.reason}",
                raw_response=None,
            ) from error

        try:
            response_payload = json.loads(raw_body)
        except json.JSONDecodeError as error:
            raise AIMentorResponseError(
                f"Ollama returned non-JSON body: {error}",
                raw_response=raw_body,
            ) from error

        message = response_payload.get("message", {})
        raw_content = message.get("content") if isinstance(message, dict) else None
        if not raw_content or not isinstance(raw_content, str):
            raise AIMentorResponseError(
                "Ollama returned an empty or malformed message content.",
                raw_response=raw_body,
            )
        return str(raw_content)
