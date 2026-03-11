class InvalidCodeError(Exception):
    """
    Exception raised when the code is invalid.
    Stores the original error message and/or code lines in a log attribute,
    without exposing implementation details.
    """

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
        """
        Returns sanitized log info (message and/or lines),
        without exposing domain implementation details.
        """
        return self._log
