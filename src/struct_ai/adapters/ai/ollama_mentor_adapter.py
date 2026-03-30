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

from pydantic import ValidationError

from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.entities.suggestion import Suggestion
from struct_ai.core.exceptions.exceptions import AIMentorResponseError
from struct_ai.core.interfaces.ai_mentor_port import AIMentorPort

_DEFAULT_BASE_URL: Final[str] = "http://localhost:11434"
_DEFAULT_MODEL: Final[str] = "llama3"
_REQUEST_TIMEOUT_SECONDS: Final[int] = 120

_SYSTEM_PROMPT: Final[str] = """
You are a strict but educational Clean Architecture mentor specialized in Python.
Your sole purpose is to review code that violates a specific architectural rule and
produce a structured, Socratic refactoring suggestion.

Rules you enforce:
- Immutability: domain entities must be frozen (use Pydantic frozen models or dataclasses(frozen=True)).
- Separation of concerns: each module has one responsibility; side effects belong in adapters.
- Layer isolation: domain code (core/) must never import from adapters/ or entrypoints/.
- Dependency Inversion: domain depends on abstractions (ports), never on concrete adapters.

Response format — you MUST reply with a valid JSON object and nothing else:
{
  "concept_name": "<name of the violated principle>",
  "educational_explanation": "<Socratic explanation of why this violates the rule and how to think about it>",
  "code_before": "<the original offending snippet, verbatim>",
  "code_after": "<refactored snippet that respects immutability and separation of concerns>",
  "documentation_links": ["<optional URL>"]
}

Constraints:
- The refactored code in code_after MUST respect immutability (no mutation of shared state).
- Do NOT include markdown fences, prose, or keys outside the JSON schema above.
- If you cannot suggest a safe refactoring, explain why in educational_explanation and
  leave code_after identical to code_before.
""".strip()


class OllamaMentorAdapter(AIMentorPort):
    """
    Calls a locally running Ollama server via its REST API to generate
    Socratic refactoring suggestions.

    No external SDK required — communicates over HTTP using urllib from the
    standard library. The server URL and model are resolved from environment
    variables with sane defaults.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url: str = (
            base_url
            or os.environ.get("OLLAMA_BASE_URL")
            or _DEFAULT_BASE_URL
        ).rstrip("/")
        self._model: str = model or os.environ.get("OLLAMA_MODEL") or _DEFAULT_MODEL

    def suggest(self, code_snippet: str, violated_rule: RuleType) -> Suggestion:
        """
        Generate a pedagogical Suggestion for the given violation.

        Raises:
            AIMentorResponseError: when the server is unreachable, returns a
                non-200 status, malformed JSON, or a payload that does not
                match the Suggestion schema.
        """
        user_message = self._build_user_message(code_snippet, violated_rule)
        raw_response = self._call_api(user_message)
        return self._parse_response(raw_response)

    def _build_user_message(self, code_snippet: str, violated_rule: RuleType) -> str:
        return (
            f"The following Python code violates the '{violated_rule.value}' rule:\n\n"
            f"```python\n{code_snippet}\n```\n\n"
            "Provide a structured refactoring suggestion in the JSON format described."
        )

    def _call_api(self, user_message: str) -> str:
        endpoint = f"{self._base_url}/api/chat"
        body = json.dumps(
            {
                "model": self._model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
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
        content = message.get("content") if isinstance(message, dict) else None
        if not content or not isinstance(content, str):
            raise AIMentorResponseError(
                "Ollama returned an empty or malformed message content.",
                raw_response=raw_body,
            )
        return content

    def _parse_response(self, raw_response: str) -> Suggestion:
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as error:
            raise AIMentorResponseError(
                f"Ollama model response is not valid JSON: {error}",
                raw_response=raw_response,
            ) from error

        try:
            return Suggestion(**payload)
        except (ValidationError, TypeError) as error:
            raise AIMentorResponseError(
                f"Ollama model response does not match the Suggestion schema: {error}",
                raw_response=raw_response,
            ) from error
