from pathlib import Path

from struct_ai.core.interfaces.inputs.source_file_reader_port import SourceFileReaderPort


class PathlibSourceFileReader(SourceFileReaderPort):
    """Reads source files using pathlib (UTF-8)."""

    def read_text(self, file_path: str) -> str:
        return Path(file_path).read_text(encoding="utf-8")
