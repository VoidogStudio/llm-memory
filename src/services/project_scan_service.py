"""Project scan service for Auto Knowledge Acquisition."""

import logging
from pathlib import Path

from src.models.acquisition import (
    ScanResult,
    ScanStatistics,
    SourceType,
)
from src.models.memory import ContentType, MemoryTier
from src.services.embedding_service import EmbeddingService
from src.services.file_hash_service import FileHashService
from src.services.memory_service import MemoryService
from src.services.namespace_service import NamespaceService
from src.utils.config_parser import extract_readme_content
from src.utils.file_scanner import (
    detect_project_type,
    extract_project_config,
    scan_directory,
)

logger = logging.getLogger(__name__)


class ProjectScanService:
    """Service for project scanning and knowledge extraction."""

    def __init__(
        self,
        memory_service: MemoryService,
        embedding_service: EmbeddingService,
        namespace_service: NamespaceService,
    ) -> None:
        """Initialize project scan service.

        Args:
            memory_service: Memory service
            embedding_service: Embedding service
            namespace_service: Namespace service
        """
        self.memory_service = memory_service
        self.embedding_service = embedding_service
        self.namespace_service = namespace_service
        self.file_hash_service = FileHashService()

    async def scan(
        self,
        project_path: str,
        namespace: str | None = None,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_file_size_kb: int = 100,
        force_rescan: bool = False,
    ) -> ScanResult:
        """Scan project and extract knowledge.

        Args:
            project_path: Path to project directory
            namespace: Target namespace (default: project name)
            include_patterns: Additional include patterns
            exclude_patterns: Additional exclude patterns
            max_file_size_kb: Maximum file size in KB
            force_rescan: Force rescan even if already scanned

        Returns:
            Scan result

        Raises:
            ValueError: If project_path is invalid
            FileNotFoundError: If project_path does not exist
        """
        # Validate and resolve path
        try:
            root_path = Path(project_path).resolve()
        except Exception as e:
            raise ValueError(f"Invalid project path: {project_path}") from e

        if not root_path.exists():
            raise FileNotFoundError(f"Path does not exist: {project_path}")

        if not root_path.is_dir():
            raise ValueError(f"Path is not a directory: {project_path}")

        # Detect project type and configuration
        project_type = detect_project_type(root_path)
        detected_config = extract_project_config(root_path, project_type)

        # Determine project name
        project_name = root_path.name

        # Resolve namespace
        target_namespace = namespace or f"project_{project_name}"
        target_namespace = await self.namespace_service.resolve_namespace(target_namespace)

        # Initialize statistics
        statistics = ScanStatistics()
        categories: dict[str, int] = {}
        errors: list[dict] = []

        # Scan files
        logger.info(f"Starting scan of {project_path}")

        try:
            async for file_path, content in scan_directory(
                root_path,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                max_file_size_kb=max_file_size_kb,
                use_gitignore=True,
            ):
                statistics.files_scanned += 1

                try:
                    # Calculate file hash
                    file_hash = self.file_hash_service.calculate_hash(content)

                    # Categorize file
                    category = self._categorize_file(file_path)
                    categories[category] = categories.get(category, 0) + 1

                    # Extract content for memory
                    memory_content = self._extract_content_for_memory(
                        file_path, content, category
                    )

                    if not memory_content.strip():
                        statistics.skipped_files += 1
                        continue

                    # Prepare metadata
                    relative_path = file_path.relative_to(root_path)
                    metadata = {
                        "source_type": SourceType.PROJECT_SCAN.value,
                        "source_file": str(relative_path),
                        "file_hash": file_hash,
                        "category": category,
                        "project_name": project_name,
                        "project_type": project_type.value,
                    }

                    # Check if memory already exists with same hash (skip if force_rescan is False)
                    if not force_rescan:
                        # Search for existing memory with same source_file
                        existing_results = await self.memory_service.search(
                            query=str(relative_path),
                            namespace=target_namespace,
                            top_k=5,
                        )

                        found_existing = False
                        for result in existing_results:
                            existing_metadata = result.memory.metadata
                            if (
                                existing_metadata.get("source_file") == str(relative_path)
                                and existing_metadata.get("file_hash") == file_hash
                            ):
                                # File unchanged, skip
                                found_existing = True
                                statistics.skipped_files += 1
                                break

                        if found_existing:
                            continue

                    # Store or update memory
                    tags = [category, project_type.value, "project_scan"]

                    try:
                        await self.memory_service.store(
                            content=memory_content,
                            content_type=self._map_category_to_content_type(category),
                            memory_tier=MemoryTier.LONG_TERM,
                            tags=tags,
                            metadata=metadata,
                            namespace=target_namespace,
                        )
                        statistics.memories_created += 1

                    except Exception as e:
                        logger.error(f"Error storing memory for {file_path}: {e}")
                        statistics.errors += 1
                        errors.append({
                            "file": str(relative_path),
                            "error": str(e),
                            "type": "storage_error",
                        })

                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    statistics.errors += 1
                    errors.append({
                        "file": str(file_path.relative_to(root_path)),
                        "error": str(e),
                        "type": "processing_error",
                    })

        except Exception as e:
            logger.error(f"Error scanning directory {project_path}: {e}")
            errors.append({
                "file": None,
                "error": str(e),
                "type": "scan_error",
            })

        # Extract README content and store as project overview
        readme_content = extract_readme_content(root_path)
        if readme_content:
            try:
                metadata = {
                    "source_type": SourceType.PROJECT_SCAN.value,
                    "source_file": "README",
                    "category": "documentation",
                    "project_name": project_name,
                    "project_type": project_type.value,
                }

                await self.memory_service.store(
                    content=readme_content,
                    content_type=ContentType.TEXT,
                    memory_tier=MemoryTier.LONG_TERM,
                    tags=["documentation", "readme", "project_overview"],
                    metadata=metadata,
                    namespace=target_namespace,
                )
                statistics.memories_created += 1

            except Exception as e:
                logger.error(f"Error storing README: {e}")
                errors.append({
                    "file": "README",
                    "error": str(e),
                    "type": "readme_error",
                })

        logger.info(
            f"Scan completed: {statistics.files_scanned} files scanned, "
            f"{statistics.memories_created} memories created, "
            f"{statistics.errors} errors"
        )

        return ScanResult(
            project_name=project_name,
            namespace=target_namespace,
            statistics=statistics,
            project_type=project_type,
            detected_config=detected_config,
            categories=categories,
            errors=errors,
        )

    def _categorize_file(self, file_path: Path) -> str:
        """Categorize file based on extension and path.

        Args:
            file_path: File path

        Returns:
            Category name
        """
        file_name = file_path.name.lower()
        file_ext = file_path.suffix.lower()
        path_str = str(file_path).lower()

        # Configuration files
        if file_name in [
            "pyproject.toml",
            "package.json",
            "cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            ".gitignore",
            "dockerfile",
            "makefile",
        ] or file_ext in [".toml", ".yaml", ".yml", ".json", ".xml", ".ini", ".cfg"]:
            return "config"

        # Documentation
        if file_ext in [".md", ".rst", ".txt"] or file_name.startswith("readme"):
            return "documentation"

        # Test files
        if "test" in path_str or file_name.startswith("test_") or file_name.endswith("_test"):
            return "test"

        # Source code
        if file_ext in [
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".rs",
            ".go",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
        ]:
            return "source_code"

        return "other"

    def _extract_content_for_memory(
        self, file_path: Path, content: str, category: str
    ) -> str:
        """Extract relevant content for memory storage.

        Args:
            file_path: File path
            content: File content
            category: File category

        Returns:
            Extracted content
        """
        # For documentation, use full content
        if category == "documentation":
            return content

        # For config files, create a structured summary
        if category == "config":
            lines = content.splitlines()
            # Limit to first 100 lines for config files
            if len(lines) > 100:
                return "\n".join(lines[:100]) + "\n... (truncated)"
            return content

        # For source code, extract docstrings and comments
        if category == "source_code":
            # For now, use full content (could be improved to extract only docstrings/comments)
            lines = content.splitlines()
            # Limit to first 200 lines
            if len(lines) > 200:
                return "\n".join(lines[:200]) + "\n... (truncated)"
            return content

        # For test files, extract test names and docstrings
        if category == "test":
            lines = content.splitlines()
            # Limit to first 150 lines
            if len(lines) > 150:
                return "\n".join(lines[:150]) + "\n... (truncated)"
            return content

        # For other files, use limited content
        lines = content.splitlines()
        if len(lines) > 50:
            return "\n".join(lines[:50]) + "\n... (truncated)"
        return content

    def _map_category_to_content_type(self, category: str) -> ContentType:
        """Map file category to content type.

        Args:
            category: File category

        Returns:
            Content type
        """
        if category == "source_code":
            return ContentType.CODE
        if category == "config":
            return ContentType.YAML
        return ContentType.TEXT
