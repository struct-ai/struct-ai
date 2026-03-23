from pathlib import Path


class ConfigNotFoundError(Exception):
    """Raised when .struct-ia.yaml does not exist at the project root."""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Configuration file not found: {path}")


class InvalidConfigError(Exception):
    """Raised when .struct-ia.yaml is malformed or fails Pydantic validation."""

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"Invalid configuration file {path}: {detail}")


class InvalidCodeError(Exception):
    def __init__(
        self,
        message: str | None = None,
        *,
        lines: list[str] | None = None,
    ) -> None:
        super().__init__("Invalid code error.")
        self._log: dict[str, object | None] = {
            "message": message,
            "lines": lines,
        }

    @property
    def log(self) -> dict[str, object | None]:
        return self._log


class AIMentorResponseError(Exception):
    """
    Raised when the LLM response cannot be deserialized into a valid Suggestion.

    Carries the raw response string so callers can log or debug the malformed payload.
    """

    def __init__(self, message: str, *, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response
