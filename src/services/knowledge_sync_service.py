"""Knowledge sync service for Auto Knowledge Acquisition."""

import logging
from pathlib import Path

from src.models.acquisition import (
    SourceType,
    SyncDocumentInfo,
    SyncResult,
    SyncSourceType,
    SyncStatistics,
)
from src.services.embedding_service import EmbeddingService
from src.services.file_hash_service import FileHashService
from src.services.knowledge_service import KnowledgeService
from src.utils.file_scanner import scan_directory

logger = logging.getLogger(__name__)


class KnowledgeSyncService:
    """Service for knowledge synchronization from external sources."""

    def __init__(
        self,
        knowledge_service: KnowledgeService,
        embedding_service: EmbeddingService,
        file_hash_service: FileHashService,
    ) -> None:
        """Initialize knowledge sync service.

        Args:
            knowledge_service: Knowledge service
            embedding_service: Embedding service
            file_hash_service: File hash service
        """
        self.knowledge_service = knowledge_service
        self.embedding_service = embedding_service
        self.file_hash_service = file_hash_service

    async def sync(
        self,
        source_type: str,
        source_path: str,
        namespace: str | None = None,
        category: str = "external_docs",
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        update_mode: str = "smart",
    ) -> SyncResult:
        """Sync knowledge from external source.

        Args:
            source_type: Source type (local_file/local_directory/url/github_repo)
            source_path: Source path or URL
            namespace: Target namespace
            category: Document category
            include_patterns: Include patterns for directories
            exclude_patterns: Exclude patterns for directories
            chunk_size: Characters per chunk
            chunk_overlap: Chunk overlap
            update_mode: Update mode (smart/full)

        Returns:
            Sync result

        Raises:
            ValueError: If source_type is invalid
            FileNotFoundError: If source does not exist
        """
        # Validate source type
        try:
            sync_source_type = SyncSourceType(source_type)
        except ValueError as e:
            raise ValueError(
                f"Invalid source_type: {source_type}. "
                f"Must be one of: {', '.join([t.value for t in SyncSourceType])}"
            ) from e

        # Initialize statistics
        statistics = SyncStatistics()
        documents: list[SyncDocumentInfo] = []
        errors: list[dict] = []

        # Dispatch based on source type
        try:
            if sync_source_type == SyncSourceType.LOCAL_FILE:
                doc_info, stats = await self._sync_local_file(
                    file_path=Path(source_path),
                    category=category,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    update_mode=update_mode,
                )
                documents.append(doc_info)
                statistics = stats

            elif sync_source_type == SyncSourceType.LOCAL_DIRECTORY:
                docs, stats = await self._sync_local_directory(
                    dir_path=Path(source_path),
                    category=category,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    update_mode=update_mode,
                )
                documents.extend(docs)
                statistics = stats

            elif sync_source_type == SyncSourceType.URL:
                # URL sync not implemented in this version
                raise NotImplementedError("URL sync not yet implemented")

            elif sync_source_type == SyncSourceType.GITHUB_REPO:
                # GitHub sync not implemented in this version
                raise NotImplementedError("GitHub sync not yet implemented")

        except FileNotFoundError as e:
            logger.error(f"Source not found: {source_path}")
            errors.append({
                "source": source_path,
                "error": str(e),
                "type": "file_not_found",
            })
            raise

        except Exception as e:
            logger.error(f"Error syncing from {source_path}: {e}")
            errors.append({
                "source": source_path,
                "error": str(e),
                "type": "sync_error",
            })

        logger.info(
            f"Sync completed: {statistics.files_processed} files, "
            f"{statistics.chunks_created} chunks created"
        )

        return SyncResult(
            source_type=sync_source_type,
            source_path=source_path,
            statistics=statistics,
            documents=documents,
            errors=errors,
        )

    async def _sync_local_file(
        self,
        file_path: Path,
        category: str,
        chunk_size: int,
        chunk_overlap: int,
        update_mode: str,
    ) -> tuple[SyncDocumentInfo, SyncStatistics]:
        """Sync a local file.

        Args:
            file_path: File path
            category: Document category
            chunk_size: Characters per chunk
            chunk_overlap: Chunk overlap
            update_mode: Update mode (smart/full)

        Returns:
            Tuple of (document_info, statistics)

        Raises:
            FileNotFoundError: If file does not exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        statistics = SyncStatistics(files_processed=1)

        # Read file content
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with latin-1
            with open(file_path, encoding="latin-1") as f:
                content = f.read()

        # Calculate hash
        current_hash = self.file_hash_service.calculate_hash(content)

        # Check if document needs update (smart mode)
        status = "created"
        if update_mode == "smart":
            # For smart mode, we would check existing document hash
            # For now, always create/update
            pass

        # Import document
        title = file_path.stem
        source = str(file_path)

        document, chunks_count = await self.knowledge_service.import_document(
            title=title,
            content=content,
            source=source,
            category=category,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata={
                "source_type": SourceType.KNOWLEDGE_SYNC.value,
                "file_hash": current_hash,
                "sync_source_type": SyncSourceType.LOCAL_FILE.value,
            },
            chunking_strategy="sentence",
        )

        statistics.chunks_created = chunks_count

        doc_info = SyncDocumentInfo(
            document_id=document.id,
            title=title,
            source_file=source,
            chunks_count=chunks_count,
            status=status,
        )

        return (doc_info, statistics)

    async def _sync_local_directory(
        self,
        dir_path: Path,
        category: str,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
        chunk_size: int,
        chunk_overlap: int,
        update_mode: str,
    ) -> tuple[list[SyncDocumentInfo], SyncStatistics]:
        """Sync a local directory.

        Args:
            dir_path: Directory path
            category: Document category
            include_patterns: Include patterns
            exclude_patterns: Exclude patterns
            chunk_size: Characters per chunk
            chunk_overlap: Chunk overlap
            update_mode: Update mode (smart/full)

        Returns:
            Tuple of (documents, statistics)

        Raises:
            FileNotFoundError: If directory does not exist
        """
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        if not dir_path.is_dir():
            raise ValueError(f"Path is not a directory: {dir_path}")

        statistics = SyncStatistics()
        documents: list[SyncDocumentInfo] = []

        # Default to only markdown and text files for documentation
        if not include_patterns:
            include_patterns = ["*.md", "*.rst", "*.txt"]

        # Scan directory
        async for file_path, content in scan_directory(
            root_path=dir_path,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_file_size_kb=1000,  # Allow larger docs
            use_gitignore=True,
        ):
            statistics.files_processed += 1

            try:
                # Calculate hash
                current_hash = self.file_hash_service.calculate_hash(content)

                # Check if needs update (smart mode)
                needs_update = True
                if update_mode == "smart":
                    is_changed = await self._detect_changes(file_path, current_hash)
                    needs_update = is_changed

                if needs_update:
                    # Import document
                    title = file_path.stem
                    source = str(file_path)

                    document, chunks_count = await self.knowledge_service.import_document(
                        title=title,
                        content=content,
                        source=source,
                        category=category,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        metadata={
                            "source_type": SourceType.KNOWLEDGE_SYNC.value,
                            "file_hash": current_hash,
                            "sync_source_type": SyncSourceType.LOCAL_DIRECTORY.value,
                        },
                        chunking_strategy="sentence",
                    )

                    statistics.chunks_created += chunks_count

                    doc_info = SyncDocumentInfo(
                        document_id=document.id,
                        title=title,
                        source_file=source,
                        chunks_count=chunks_count,
                        status="created",
                    )

                    documents.append(doc_info)
                else:
                    statistics.unchanged += 1

            except Exception as e:
                logger.error(f"Error syncing file {file_path}: {e}")
                continue

        return (documents, statistics)

    async def _detect_changes(
        self,
        file_path: Path,
        stored_hash: str | None,
    ) -> bool:
        """Detect if file has changed.

        Args:
            file_path: File path
            stored_hash: Previously stored hash

        Returns:
            True if file has changed
        """
        if not stored_hash:
            return True  # No hash stored, assume changed

        try:
            current_hash = await self.file_hash_service.calculate_file_hash(file_path)
            return self.file_hash_service.is_changed(current_hash, stored_hash)
        except Exception as e:
            logger.warning(f"Error detecting changes for {file_path}: {e}")
            return True  # Assume changed on error
