"""File hash service for content change detection."""

import hashlib
import logging
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)


class FileHashService:
    """Service for file hash calculations."""

    @staticmethod
    def calculate_hash(content: str | bytes) -> str:
        """Calculate SHA-256 hash of content.

        Args:
            content: Content to hash (string or bytes)

        Returns:
            SHA-256 hash as hex string
        """
        if isinstance(content, str):
            content = content.encode("utf-8")

        hash_obj = hashlib.sha256(content)
        return hash_obj.hexdigest()

    @staticmethod
    async def calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA-256 hash of file content.

        Reads file in chunks to handle large files efficiently.

        Args:
            file_path: Path to file

        Returns:
            SHA-256 hash as hex string

        Raises:
            FileNotFoundError: If file does not exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        hash_obj = hashlib.sha256()

        try:
            async with aiofiles.open(file_path, "rb") as f:
                # Read in 8KB chunks
                while True:
                    chunk = await f.read(8192)
                    if not chunk:
                        break
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()

        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            raise

    @staticmethod
    def is_changed(current_hash: str, stored_hash: str) -> bool:
        """Check if hash has changed.

        Args:
            current_hash: Current hash value
            stored_hash: Previously stored hash value

        Returns:
            True if hashes differ (content changed)
        """
        return current_hash != stored_hash
