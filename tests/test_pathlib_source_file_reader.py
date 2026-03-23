"""Tests for PathlibSourceFileReader."""

import tempfile
from pathlib import Path

import pytest

from struct_ai.adapters.io.pathlib_source_file_reader import PathlibSourceFileReader


def describe_PathlibSourceFileReader() -> None:
    def describe_read_text() -> None:
        def it_returns_utf8_file_contents() -> None:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", delete=False
            ) as handle:
                handle.write("alpha\nβ\n")
                path = handle.name
            try:
                assert PathlibSourceFileReader().read_text(path) == "alpha\nβ\n"
            finally:
                Path(path).unlink(missing_ok=True)

        def it_raises_file_not_found_for_missing_path() -> None:
            missing = str(Path(tempfile.gettempdir()) / "struct_ai_missing_xyz.py")
            with pytest.raises(FileNotFoundError):
                PathlibSourceFileReader().read_text(missing)
