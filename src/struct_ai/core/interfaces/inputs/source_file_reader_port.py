from abc import ABC, abstractmethod


class SourceFileReaderPort(ABC):
    """
    Port for reading UTF-8 text from a file path.

    Core use cases depend on this abstraction instead of calling pathlib or
    open() directly, so filesystem I/O stays behind an adapter.
    """

    @abstractmethod
    def read_text(self, file_path: str) -> str:
        """
        Read the entire file as UTF-8 text.

        Raises:
            FileNotFoundError: When the path does not exist.
            OSError: For other I/O failures (permission, etc.).
        """
        raise NotImplementedError("Subclasses must implement this method.")
