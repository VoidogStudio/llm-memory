"""Configuration file parsers."""

import json
import logging
from pathlib import Path
from typing import Any

import tomllib

logger = logging.getLogger(__name__)


def parse_pyproject_toml(file_path: Path) -> dict[str, Any]:
    """Parse pyproject.toml file.

    Args:
        file_path: Path to pyproject.toml

    Returns:
        Parsed TOML data as dictionary

    Raises:
        FileNotFoundError: If file does not exist
        tomllib.TOMLDecodeError: If TOML parsing fails
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
        logger.debug(f"Successfully parsed {file_path}")
        return data
    except tomllib.TOMLDecodeError as e:
        logger.error(f"Failed to parse TOML file {file_path}: {e}")
        raise


def parse_package_json(file_path: Path) -> dict[str, Any]:
    """Parse package.json file.

    Args:
        file_path: Path to package.json

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If JSON parsing fails
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(f"Successfully parsed {file_path}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON file {file_path}: {e}")
        raise


def extract_readme_content(root_path: Path) -> str | None:
    """Extract README content from project root.

    Searches for README files in the following order:
    1. README.md
    2. README.rst
    3. README.txt
    4. README

    Args:
        root_path: Project root directory

    Returns:
        README content or None if not found
    """
    readme_candidates = [
        "README.md",
        "README.rst",
        "README.txt",
        "README",
        "readme.md",
        "readme.rst",
        "readme.txt",
        "readme",
    ]

    for candidate in readme_candidates:
        readme_path = root_path / candidate
        if readme_path.exists() and readme_path.is_file():
            try:
                with open(readme_path, encoding="utf-8") as f:
                    content = f.read()
                logger.debug(f"Found README at {readme_path}")
                return content
            except UnicodeDecodeError:
                # Try with latin-1 as fallback
                try:
                    with open(readme_path, encoding="latin-1") as f:
                        content = f.read()
                    logger.debug(f"Found README at {readme_path} (latin-1 encoding)")
                    return content
                except Exception as e:
                    logger.warning(f"Error reading README {readme_path}: {e}")
                    continue
            except Exception as e:
                logger.warning(f"Error reading README {readme_path}: {e}")
                continue

    logger.debug(f"No README found in {root_path}")
    return None
