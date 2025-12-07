"""Path filtering utilities using pathspec."""

import logging
from pathlib import Path

import pathspec

logger = logging.getLogger(__name__)


# Default patterns to exclude
DEFAULT_EXCLUDE_PATTERNS = [
    ".git/",
    "node_modules/",
    "__pycache__/",
    ".venv/",
    "venv/",
    ".env",
    ".env.*",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
    "*.key",
    "*.pem",
    "*.p12",
    "credentials.*",
    "secrets.*",
]


def create_path_filter(
    root_path: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    use_gitignore: bool = True,
) -> pathspec.PathSpec:
    """Create path filter using pathspec.

    Args:
        root_path: Root path for filtering
        include_patterns: Additional include patterns (gitignore format)
        exclude_patterns: Additional exclude patterns (gitignore format)
        use_gitignore: Whether to read .gitignore file

    Returns:
        Configured PathSpec object
    """
    patterns = []

    # Add default exclude patterns
    patterns.extend(DEFAULT_EXCLUDE_PATTERNS)

    # Add custom exclude patterns
    if exclude_patterns:
        patterns.extend(exclude_patterns)

    # Read .gitignore if it exists and use_gitignore is True
    if use_gitignore:
        gitignore_path = root_path / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path) as f:
                    gitignore_patterns = f.read().splitlines()
                    # Filter out comments and empty lines
                    gitignore_patterns = [
                        p.strip()
                        for p in gitignore_patterns
                        if p.strip() and not p.strip().startswith("#")
                    ]
                    patterns.extend(gitignore_patterns)
                    logger.debug(f"Loaded {len(gitignore_patterns)} patterns from .gitignore")
            except Exception as e:
                logger.warning(f"Error reading .gitignore: {e}")

    # Create PathSpec from patterns
    spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    return spec


def is_excluded(
    file_path: Path,
    root_path: Path,
    spec: pathspec.PathSpec,
) -> bool:
    """Check if file path is excluded by PathSpec.

    Args:
        file_path: File path to check
        root_path: Root path (for relative path calculation)
        spec: PathSpec object

    Returns:
        True if file should be excluded
    """
    try:
        # Get relative path from root
        rel_path = file_path.relative_to(root_path)

        # Convert to POSIX path (forward slashes) for pathspec matching
        posix_path = rel_path.as_posix()

        # Check if excluded
        return spec.match_file(posix_path)

    except ValueError:
        # file_path is not relative to root_path
        logger.warning(f"Path {file_path} is not relative to {root_path}")
        return True
    except Exception as e:
        logger.warning(f"Error checking exclusion for {file_path}: {e}")
        return True
