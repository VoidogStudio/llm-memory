"""File scanning utilities for project scan."""

import logging
from collections.abc import AsyncGenerator
from pathlib import Path

import aiofiles

from src.models.acquisition import DetectedConfig, ProjectType
from src.utils.path_filter import create_path_filter, is_excluded

logger = logging.getLogger(__name__)


async def scan_directory(
    root_path: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    max_file_size_kb: int = 100,
    use_gitignore: bool = True,
) -> AsyncGenerator[tuple[Path, str], None]:
    """Scan directory and yield file paths with contents.

    Args:
        root_path: Root directory to scan
        include_patterns: Additional include patterns
        exclude_patterns: Additional exclude patterns
        max_file_size_kb: Maximum file size in KB
        use_gitignore: Whether to use .gitignore

    Yields:
        Tuple of (file_path, content)

    Raises:
        FileNotFoundError: If root_path does not exist
        PermissionError: If insufficient permissions
    """
    if not root_path.exists():
        raise FileNotFoundError(f"Path does not exist: {root_path}")

    if not root_path.is_dir():
        raise ValueError(f"Path is not a directory: {root_path}")

    # Create path filter
    spec = create_path_filter(
        root_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        use_gitignore=use_gitignore,
    )

    max_file_size_bytes = max_file_size_kb * 1024
    visited_paths: set[Path] = set()

    for file_path in root_path.rglob("*"):
        # Skip directories
        if not file_path.is_file():
            continue

        # Check for circular symlinks
        try:
            resolved_path = file_path.resolve()
            if resolved_path in visited_paths:
                logger.warning(f"Skipping circular symlink: {file_path}")
                continue
            visited_paths.add(resolved_path)
        except (OSError, RuntimeError) as e:
            logger.warning(f"Error resolving path {file_path}: {e}")
            continue

        # Check if excluded
        if is_excluded(file_path, root_path, spec):
            continue

        # Check file size
        try:
            file_size = file_path.stat().st_size
            if file_size > max_file_size_bytes:
                logger.debug(f"Skipping large file: {file_path} ({file_size} bytes)")
                continue
        except OSError as e:
            logger.warning(f"Error getting file size for {file_path}: {e}")
            continue

        # Read file content
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()

            # Check for binary content
            if "\0" in content:
                logger.debug(f"Skipping binary file: {file_path}")
                continue

            yield (file_path, content)

        except UnicodeDecodeError:
            # Try with latin-1 as fallback
            try:
                async with aiofiles.open(file_path, encoding="latin-1") as f:
                    content = await f.read()
                    # Check for binary content
                    if "\0" in content:
                        logger.debug(f"Skipping binary file: {file_path}")
                        continue
                    yield (file_path, content)
            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {e}")
                continue

        except PermissionError:
            logger.warning(f"Permission denied: {file_path}")
            continue

        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")
            continue


def detect_project_type(root_path: Path) -> ProjectType:
    """Detect project type from root directory.

    Args:
        root_path: Project root directory

    Returns:
        Detected project type
    """
    # Python project indicators
    if (
        (root_path / "pyproject.toml").exists()
        or (root_path / "setup.py").exists()
        or (root_path / "requirements.txt").exists()
    ):
        return ProjectType.PYTHON

    # Node.js project indicators
    if (root_path / "package.json").exists():
        return ProjectType.NODEJS

    # Rust project indicators
    if (root_path / "Cargo.toml").exists():
        return ProjectType.RUST

    # Go project indicators
    if (root_path / "go.mod").exists():
        return ProjectType.GO

    # Java project indicators
    if (root_path / "pom.xml").exists() or (root_path / "build.gradle").exists():
        return ProjectType.JAVA

    return ProjectType.UNKNOWN


def extract_project_config(
    root_path: Path,
    project_type: ProjectType,
) -> DetectedConfig:
    """Extract project configuration from config files.

    Args:
        root_path: Project root directory
        project_type: Detected project type

    Returns:
        Detected configuration
    """
    config = DetectedConfig()

    if project_type == ProjectType.PYTHON:
        config.package_manager = _detect_python_package_manager(root_path)
        config.test_framework = _detect_python_test_framework(root_path)
        config.linter = _detect_python_linter(root_path)
        config.formatter = _detect_python_formatter(root_path)
        config.language_version = _detect_python_version(root_path)

    elif project_type == ProjectType.NODEJS:
        config.package_manager = _detect_nodejs_package_manager(root_path)
        config.test_framework = _detect_nodejs_test_framework(root_path)
        config.linter = _detect_nodejs_linter(root_path)
        config.formatter = _detect_nodejs_formatter(root_path)

    elif project_type == ProjectType.RUST:
        config.package_manager = "cargo"
        config.test_framework = "cargo test"
        config.linter = "clippy"
        config.formatter = "rustfmt"

    elif project_type == ProjectType.GO:
        config.package_manager = "go modules"
        config.test_framework = "go test"
        config.linter = "golangci-lint"
        config.formatter = "gofmt"

    elif project_type == ProjectType.JAVA:
        if (root_path / "pom.xml").exists():
            config.package_manager = "maven"
        elif (root_path / "build.gradle").exists():
            config.package_manager = "gradle"

    return config


def _detect_python_package_manager(root_path: Path) -> str | None:
    """Detect Python package manager."""
    if (root_path / "poetry.lock").exists():
        return "poetry"
    if (root_path / "Pipfile").exists():
        return "pipenv"
    if (root_path / "pyproject.toml").exists():
        return "pip"
    if (root_path / "requirements.txt").exists():
        return "pip"
    return None


def _detect_python_test_framework(root_path: Path) -> str | None:
    """Detect Python test framework."""
    if (root_path / "pytest.ini").exists() or (root_path / "pyproject.toml").exists():
        return "pytest"
    if (root_path / "tox.ini").exists():
        return "tox"
    return None


def _detect_python_linter(root_path: Path) -> str | None:
    """Detect Python linter."""
    if (root_path / "ruff.toml").exists() or (root_path / "pyproject.toml").exists():
        return "ruff"
    if (root_path / ".pylintrc").exists():
        return "pylint"
    if (root_path / ".flake8").exists():
        return "flake8"
    return None


def _detect_python_formatter(root_path: Path) -> str | None:
    """Detect Python formatter."""
    if (root_path / "ruff.toml").exists() or (root_path / "pyproject.toml").exists():
        return "ruff"
    if (root_path / "pyproject.toml").exists():
        return "black"
    return None


def _detect_python_version(root_path: Path) -> str | None:
    """Detect Python version from config files."""
    pyproject_path = root_path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomllib

            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                # Try to get version from project.requires-python
                if "project" in data and "requires-python" in data["project"]:
                    return data["project"]["requires-python"]
        except Exception:
            pass
    return None


def _detect_nodejs_package_manager(root_path: Path) -> str | None:
    """Detect Node.js package manager."""
    if (root_path / "package-lock.json").exists():
        return "npm"
    if (root_path / "yarn.lock").exists():
        return "yarn"
    if (root_path / "pnpm-lock.yaml").exists():
        return "pnpm"
    return None


def _detect_nodejs_test_framework(root_path: Path) -> str | None:
    """Detect Node.js test framework."""
    package_json = root_path / "package.json"
    if package_json.exists():
        try:
            import json

            with open(package_json) as f:
                data = json.load(f)
                dev_deps = data.get("devDependencies", {})
                if "jest" in dev_deps:
                    return "jest"
                if "mocha" in dev_deps:
                    return "mocha"
                if "vitest" in dev_deps:
                    return "vitest"
        except Exception:
            pass
    return None


def _detect_nodejs_linter(root_path: Path) -> str | None:
    """Detect Node.js linter."""
    if (root_path / ".eslintrc.js").exists() or (root_path / ".eslintrc.json").exists():
        return "eslint"
    return None


def _detect_nodejs_formatter(root_path: Path) -> str | None:
    """Detect Node.js formatter."""
    if (root_path / ".prettierrc").exists() or (root_path / ".prettierrc.json").exists():
        return "prettier"
    return None
