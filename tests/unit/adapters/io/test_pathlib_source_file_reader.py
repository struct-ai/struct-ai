"""Unit tests for PathlibSourceFileReader."""

import tempfile
from pathlib import Path

import pytest

from struct_ai.adapters.io.pathlib_source_file_reader import PathlibSourceFileReader


def test_read_text_returns_utf8_contents() -> None:
    reader = PathlibSourceFileReader()
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as handle:
        handle.write("alpha\nβ\n")
        path = handle.name
    try:
        assert reader.read_text(path) == "alpha\nβ\n"
    finally:
        Path(path).unlink(missing_ok=True)


def test_read_text_raises_file_not_found() -> None:
    reader = PathlibSourceFileReader()
    missing = str(Path(tempfile.gettempdir()) / "struct_ai_missing_file_xyz.py")
    with pytest.raises(FileNotFoundError):
        reader.read_text(missing)
