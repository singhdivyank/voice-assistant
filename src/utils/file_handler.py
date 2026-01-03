"""File handling utilities."""

import logging
from pathlib import Path
from typing import Optional

from src.utils.exceptions import FileOperationError


logger = logging.getLogger(__name__)


class FileHandler:
    """Handles file operations with proper error handling and cleanup"""

    @staticmethod
    def safe_delete(file_path: Path) -> bool:
        """
        Safely delete a file if it exists.

        Args:
            file_path: Path to the file to delete

        Returns:
            True if the file was deleted, False if it didn't exist

        Raises:
            FileOperationError: If deletion fails
        """

        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug("Deleted file: %s", file_path)
                return True

            return False
        except PermissionError as e:
            raise FileOperationError(
                f"Permission denied while deleting {file_path}: {e}"
            ) from e
        except OSError as e:
            raise FileOperationError(f"Failed to delete {file_path}: {e}") from e

    @staticmethod
    def safe_write(file_path: Path, content: str, encoding: str = "utf-8") -> None:
        """
        Safely write content to a file.

        Args:
            file_path: Path to write to
            content: Content to write
            encoding: File encoding

        Raises:
            FileOperationError: If write fails
        """

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding=encoding)
            logger.debug("Written to file: %s", file_path)
        except PermissionError as e:
            raise FileOperationError(f"Permission denied writing to {file_path}: {e}") from e
        except OSError as e:
            raise FileOperationError(f"Failed to write to {file_path}: {e}") from e

    @staticmethod
    def safe_read(file_path: Path, encoding: str = "utf-8") -> Optional[str]:
        """
        Safely read content from a file.

        Args:
            file_path: Path to read from
            encoding: File encoding

        Returns:
            File content or None if file doesn't exist

        Raises:
            FileOperationError: If read fails
        """

        try:
            if not file_path.exists():
                return None

            return file_path.read_text(encoding=encoding)
        except PermissionError as e:
            raise FileOperationError(f"Permission denied reading {file_path}: {e}") from e
        except OSError as e:
            raise FileOperationError(f"Failed to read {file_path}: {e}") from e
