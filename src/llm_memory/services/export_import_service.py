"""Service for database export/import."""

import json
import os
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_memory.db.database import Database
from llm_memory.db.repositories.agent_repository import AgentRepository
from llm_memory.db.repositories.knowledge_repository import KnowledgeRepository
from llm_memory.db.repositories.memory_repository import MemoryRepository
from llm_memory.models.export_import import ExportResult, ImportResult
from llm_memory.services.embedding_service import EmbeddingService


class ExportImportService:
    """Service for database export/import."""

    SUPPORTED_SCHEMA_VERSIONS = [1, 2, 3]
    CURRENT_SCHEMA_VERSION = 3
    BATCH_SIZE = 100

    def __init__(
        self,
        memory_repository: MemoryRepository,
        knowledge_repository: KnowledgeRepository,
        agent_repository: AgentRepository,
        db: Database,
        embedding_service: EmbeddingService | None = None,
        allowed_paths: list[Path] | None = None,
    ) -> None:
        """Initialize export/import service.

        Args:
            memory_repository: Memory repository
            knowledge_repository: Knowledge repository
            agent_repository: Agent repository
            db: Database instance
            embedding_service: Embedding service (optional)
            allowed_paths: Additional allowed base directories for path validation (for testing)
        """
        self.memory_repository = memory_repository
        self.knowledge_repository = knowledge_repository
        self.agent_repository = agent_repository
        self.db = db
        self.embedding_service = embedding_service
        self.allowed_paths = [p.resolve() for p in (allowed_paths or [])]

    def _validate_safe_path(self, file_path: str, base_dir: str | None = None) -> Path:
        """Validate that file path is safe and within allowed directory.

        Args:
            file_path: User-provided file path
            base_dir: Base directory to constrain paths (default: cwd)

        Returns:
            Resolved absolute Path

        Raises:
            ValueError: If path is outside base_dir or uses path traversal
        """
        # Additional check for path traversal patterns (before resolving)
        if ".." in Path(file_path).parts:
            raise ValueError(f"Path traversal detected in {file_path}")

        # Resolve to absolute path (handles symlinks like /var -> /private/var on macOS)
        path_resolved = Path(file_path).resolve()

        # Define base directories (default to current working directory + allowed_paths)
        allowed_bases = []
        if base_dir:
            allowed_bases.append(Path(base_dir).resolve())
        else:
            allowed_bases.append(Path.cwd().resolve())

        # Add any additional allowed paths (e.g., /tmp for tests)
        # Note: self.allowed_paths are already resolved in __init__
        allowed_bases.extend(self.allowed_paths)

        # Check if path is within at least one allowed base directory
        # Both paths are already resolved to handle symlinks (e.g., /var -> /private/var on macOS)
        path_allowed = False
        for base_resolved in allowed_bases:
            try:
                path_resolved.relative_to(base_resolved)
                path_allowed = True
                break
            except ValueError:
                continue

        if not path_allowed:
            raise ValueError(f"Path {file_path} is outside allowed directory")

        return path_resolved

    async def export_database(
        self,
        output_path: str,
        include_embeddings: bool = True,
        memory_tier: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        format: str = "jsonl",
    ) -> ExportResult:
        """Export database to file.

        Args:
            output_path: Output file path
            include_embeddings: Include embedding vectors
            memory_tier: Filter by tier
            created_after: Filter by creation date
            created_before: Filter by creation date
            format: Output format ("jsonl")

        Returns:
            ExportResult with counts and file info

        Raises:
            ValueError: If format not supported
            IOError: If file cannot be written
        """
        if format != "jsonl":
            raise ValueError(f"Unsupported format: {format}")

        # Validate path safety
        output_path_safe = self._validate_safe_path(output_path)

        # Ensure output directory exists
        output_dir = output_path_safe.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize counts
        counts: dict[str, int] = {
            "memories": 0,
            "knowledge_documents": 0,
            "knowledge_chunks": 0,
            "agents": 0,
            "messages": 0,
            "memory_links": 0,
            "decay_config": 0,
        }

        exported_at = datetime.now(timezone.utc)

        # Open file for writing
        try:
            with open(output_path_safe, "w", encoding="utf-8") as f:
                # Write metadata (first line)
                metadata_dict = {
                    "schema_version": self.CURRENT_SCHEMA_VERSION,
                    "exported_at": exported_at.isoformat(),
                    "counts": counts,  # Will be updated
                }
                f.write(json.dumps(metadata_dict) + "\n")

                # Export memories with filtering
                where_clauses = []
                params = []

                if memory_tier:
                    where_clauses.append("memory_tier = ?")
                    params.append(memory_tier)

                if created_after:
                    where_clauses.append("created_at >= ?")
                    params.append(created_after.isoformat())

                if created_before:
                    where_clauses.append("created_at <= ?")
                    params.append(created_before.isoformat())

                if where_clauses:
                    where_sql = " WHERE " + " AND ".join(where_clauses)
                else:
                    where_sql = ""

                cursor = await self.db.execute(
                    f"SELECT * FROM memories{where_sql}",
                    tuple(params) if params else (),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    memory_data = dict(row)

                    # Get embedding if requested
                    if include_embeddings:
                        emb_cursor = await self.db.execute(
                            "SELECT embedding FROM embeddings WHERE memory_id = ?",
                            (memory_data["id"],),
                        )
                        emb_row = await emb_cursor.fetchone()
                        if emb_row:
                            # sqlite-vec returns embedding as float32 binary (bytes)
                            embedding_bytes = emb_row["embedding"]
                            if isinstance(embedding_bytes, bytes):
                                # Convert binary to list[float]
                                dimensions = len(embedding_bytes) // 4  # 4 bytes per float32
                                memory_data["embedding"] = list(struct.unpack(f'{dimensions}f', embedding_bytes))
                            else:
                                # Fallback for JSON string (backward compatibility)
                                memory_data["embedding"] = json.loads(embedding_bytes)

                    record = {"type": "memory", **memory_data}
                    f.write(json.dumps(record) + "\n")
                    counts["memories"] += 1

                # Export knowledge documents
                cursor = await self.db.execute("SELECT * FROM knowledge_documents")
                rows = await cursor.fetchall()
                for row in rows:
                    record = {"type": "knowledge_document", **dict(row)}
                    f.write(json.dumps(record) + "\n")
                    counts["knowledge_documents"] += 1

                # Export knowledge chunks
                cursor = await self.db.execute("SELECT * FROM knowledge_chunks")
                rows = await cursor.fetchall()
                for row in rows:
                    chunk_data = dict(row)

                    # Get embedding if requested
                    if include_embeddings:
                        emb_cursor = await self.db.execute(
                            "SELECT embedding FROM chunk_embeddings WHERE chunk_id = ?",
                            (chunk_data["id"],),
                        )
                        emb_row = await emb_cursor.fetchone()
                        if emb_row:
                            # sqlite-vec returns embedding as float32 binary (bytes)
                            embedding_bytes = emb_row["embedding"]
                            if isinstance(embedding_bytes, bytes):
                                # Convert binary to list[float]
                                dimensions = len(embedding_bytes) // 4  # 4 bytes per float32
                                chunk_data["embedding"] = list(struct.unpack(f'{dimensions}f', embedding_bytes))
                            else:
                                # Fallback for JSON string (backward compatibility)
                                chunk_data["embedding"] = json.loads(embedding_bytes)

                    record = {"type": "knowledge_chunk", **chunk_data}
                    f.write(json.dumps(record) + "\n")
                    counts["knowledge_chunks"] += 1

                # Export agents
                cursor = await self.db.execute("SELECT * FROM agents")
                rows = await cursor.fetchall()
                for row in rows:
                    record = {"type": "agent", **dict(row)}
                    f.write(json.dumps(record) + "\n")
                    counts["agents"] += 1

                # Export messages
                cursor = await self.db.execute("SELECT * FROM messages")
                rows = await cursor.fetchall()
                for row in rows:
                    record = {"type": "message", **dict(row)}
                    f.write(json.dumps(record) + "\n")
                    counts["messages"] += 1

                # Export memory links
                cursor = await self.db.execute("SELECT * FROM memory_links")
                rows = await cursor.fetchall()
                for row in rows:
                    record = {"type": "memory_link", **dict(row)}
                    f.write(json.dumps(record) + "\n")
                    counts["memory_links"] += 1

                # Export decay config
                cursor = await self.db.execute("SELECT * FROM decay_config WHERE id = 1")
                row = await cursor.fetchone()
                if row:
                    record = {"type": "decay_config", **dict(row)}
                    f.write(json.dumps(record) + "\n")
                    counts["decay_config"] += 1

            # Get file size
            file_size = os.path.getsize(output_path_safe)

        except OSError as e:
            raise OSError(f"Failed to write export file: {e}") from e

        return ExportResult(
            exported_at=exported_at,
            schema_version=self.CURRENT_SCHEMA_VERSION,
            counts=counts,
            file_path=str(output_path_safe),
            file_size_bytes=file_size,
        )

    async def import_database(
        self,
        input_path: str,
        mode: str = "merge",
        on_conflict: str = "skip",
        regenerate_embeddings: bool = False,
        use_transaction: bool = True,
    ) -> ImportResult:
        """Import database from file.

        Args:
            input_path: Input file path
            mode: Import mode ("replace" | "merge")
            on_conflict: Conflict handling ("skip" | "update" | "error")
            regenerate_embeddings: Regenerate embeddings from content
            use_transaction: Use explicit transactions (default True)

        Returns:
            ImportResult with counts

        Raises:
            ValueError: If schema version incompatible or mode invalid
            IOError: If file cannot be read
        """
        if mode not in ["replace", "merge"]:
            raise ValueError(f"Invalid mode: {mode}")

        if on_conflict not in ["skip", "update", "error"]:
            raise ValueError(f"Invalid on_conflict: {on_conflict}")

        # Validate path safety
        input_path_safe = self._validate_safe_path(input_path)

        if not input_path_safe.exists():
            raise OSError(f"Import file not found: {input_path}")

        # Initialize counts
        counts: dict[str, int] = {
            "memories": 0,
            "knowledge_documents": 0,
            "knowledge_chunks": 0,
            "agents": 0,
            "messages": 0,
            "memory_links": 0,
            "decay_config": 0,
        }
        skipped_count = 0
        error_count = 0
        errors: list[dict[str, Any]] = []

        try:
            with open(input_path_safe, encoding="utf-8") as f:
                # Read and validate metadata
                metadata_line = f.readline()
                metadata = json.loads(metadata_line)
                schema_version = metadata.get("schema_version", 1)

                if schema_version > self.CURRENT_SCHEMA_VERSION:
                    raise ValueError(
                        f"Unsupported schema version: {schema_version}. "
                        f"Maximum supported: {self.CURRENT_SCHEMA_VERSION}"
                    )

                # Replace mode: clear existing data
                if mode == "replace":
                    if use_transaction:
                        async with self.db.transaction():
                            await self.db.execute("DELETE FROM memories")
                            await self.db.execute("DELETE FROM knowledge_documents")
                            await self.db.execute("DELETE FROM agents")
                            await self.db.execute("DELETE FROM memory_links")
                            # Note: CASCADE DELETE will handle related tables
                    else:
                        await self.db.execute("DELETE FROM memories")
                        await self.db.execute("DELETE FROM knowledge_documents")
                        await self.db.execute("DELETE FROM agents")
                        await self.db.execute("DELETE FROM memory_links")
                        # Note: CASCADE DELETE will handle related tables

                # Import records
                if use_transaction:
                    async with self.db.transaction():
                        await self._process_import_records(
                            f, on_conflict, regenerate_embeddings, counts, errors
                        )
                else:
                    await self._process_import_records(
                        f, on_conflict, regenerate_embeddings, counts, errors
                    )

        except OSError as e:
            raise OSError(f"Failed to read import file: {e}") from e

        return ImportResult(
            imported_at=datetime.now(timezone.utc),
            schema_version=schema_version,
            mode=mode,
            counts=counts,
            skipped_count=skipped_count,
            error_count=error_count,
            errors=errors,
        )

    async def _process_import_records(
        self,
        file_handle: Any,
        on_conflict: str,
        regenerate_embeddings: bool,
        counts: dict[str, int],
        errors: list[dict[str, Any]],
    ) -> None:
        """Process import records from file.

        Args:
            file_handle: File handle to read from
            on_conflict: Conflict handling mode
            regenerate_embeddings: Whether to regenerate embeddings
            counts: Dictionary to update with import counts
            errors: List to append errors to
        """
        skipped_count = 0
        error_count = 0

        for line in file_handle:
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                record_type = record.get("type")

                if record_type == "memory":
                    success = await self._import_memory(
                        record, on_conflict, regenerate_embeddings
                    )
                    if success:
                        counts["memories"] += 1
                    else:
                        skipped_count += 1

                elif record_type == "knowledge_document":
                    success = await self._import_document(record, on_conflict)
                    if success:
                        counts["knowledge_documents"] += 1
                    else:
                        skipped_count += 1

                elif record_type == "knowledge_chunk":
                    success = await self._import_chunk(
                        record, on_conflict, regenerate_embeddings
                    )
                    if success:
                        counts["knowledge_chunks"] += 1
                    else:
                        skipped_count += 1

                elif record_type == "agent":
                    success = await self._import_agent(record, on_conflict)
                    if success:
                        counts["agents"] += 1
                    else:
                        skipped_count += 1

                elif record_type == "message":
                    success = await self._import_message(record, on_conflict)
                    if success:
                        counts["messages"] += 1
                    else:
                        skipped_count += 1

                elif record_type == "memory_link":
                    success = await self._import_link(record, on_conflict)
                    if success:
                        counts["memory_links"] += 1
                    else:
                        skipped_count += 1

                elif record_type == "decay_config":
                    success = await self._import_decay_config(record)
                    if success:
                        counts["decay_config"] += 1

            except Exception as e:
                error_count += 1
                errors.append({
                    "record_type": record.get("type", "unknown"),
                    "id": record.get("id", "unknown"),
                    "error": str(e),
                })
                if on_conflict == "error":
                    raise

    async def _import_memory(
        self, record: dict, on_conflict: str, regenerate_embeddings: bool
    ) -> bool:
        """Import a memory record."""
        memory_id = record["id"]

        # Check if exists
        existing = await self.memory_repository.find_by_id(memory_id)

        if existing:
            if on_conflict == "skip":
                return False
            elif on_conflict == "error":
                raise ValueError(f"Memory already exists: {memory_id}")
            # on_conflict == "update" falls through to upsert

        # Insert/update memory
        await self.db.execute(
            """
            INSERT OR REPLACE INTO memories (
                id, content, content_type, memory_tier, tags, metadata,
                agent_id, created_at, updated_at, expires_at,
                importance_score, access_count, last_accessed_at, consolidated_from
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["content"],
                record["content_type"],
                record["memory_tier"],
                record["tags"],
                record["metadata"],
                record.get("agent_id"),
                record["created_at"],
                record["updated_at"],
                record.get("expires_at"),
                record.get("importance_score", 0.5),
                record.get("access_count", 0),
                record.get("last_accessed_at"),
                record.get("consolidated_from"),
            ),
        )

        # Handle embedding
        if "embedding" in record and not regenerate_embeddings:
            await self.db.execute(
                "INSERT OR REPLACE INTO embeddings (memory_id, embedding) VALUES (?, ?)",
                (memory_id, json.dumps(record["embedding"])),
            )
        elif regenerate_embeddings and self.embedding_service:
            embedding = await self.embedding_service.generate(record["content"])
            await self.db.execute(
                "INSERT OR REPLACE INTO embeddings (memory_id, embedding) VALUES (?, ?)",
                (memory_id, json.dumps(embedding)),
            )

        return True

    async def _import_document(self, record: dict, on_conflict: str) -> bool:
        """Import a knowledge document record."""
        doc_id = record["id"]

        # Check if exists
        existing = await self.knowledge_repository.find_document(doc_id)

        if existing:
            if on_conflict == "skip":
                return False
            elif on_conflict == "error":
                raise ValueError(f"Document already exists: {doc_id}")

        await self.db.execute(
            """
            INSERT OR REPLACE INTO knowledge_documents (
                id, title, source, category, version, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["title"],
                record.get("source"),
                record.get("category"),
                record.get("version", 1),
                record.get("metadata", "{}"),
                record["created_at"],
                record["updated_at"],
            ),
        )

        return True

    async def _import_chunk(
        self, record: dict, on_conflict: str, regenerate_embeddings: bool
    ) -> bool:
        """Import a knowledge chunk record."""
        chunk_id = record["id"]

        # Check if exists
        cursor = await self.db.execute(
            "SELECT id FROM knowledge_chunks WHERE id = ?", (chunk_id,)
        )
        existing = await cursor.fetchone()

        if existing:
            if on_conflict == "skip":
                return False
            elif on_conflict == "error":
                raise ValueError(f"Chunk already exists: {chunk_id}")

        await self.db.execute(
            """
            INSERT OR REPLACE INTO knowledge_chunks (
                id, document_id, content, chunk_index, metadata,
                section_path, has_previous, has_next
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["document_id"],
                record["content"],
                record["chunk_index"],
                record.get("metadata", "{}"),
                record.get("section_path", "[]"),
                record.get("has_previous", 0),
                record.get("has_next", 0),
            ),
        )

        # Handle embedding
        if "embedding" in record and not regenerate_embeddings:
            await self.db.execute(
                "INSERT OR REPLACE INTO chunk_embeddings (chunk_id, embedding) VALUES (?, ?)",
                (chunk_id, json.dumps(record["embedding"])),
            )
        elif regenerate_embeddings and self.embedding_service:
            embedding = await self.embedding_service.generate(record["content"])
            await self.db.execute(
                "INSERT OR REPLACE INTO chunk_embeddings (chunk_id, embedding) VALUES (?, ?)",
                (chunk_id, json.dumps(embedding)),
            )

        return True

    async def _import_agent(self, record: dict, on_conflict: str) -> bool:
        """Import an agent record."""
        agent_id = record["id"]

        # Check if exists
        existing = await self.agent_repository.find_by_id(agent_id)

        if existing:
            if on_conflict == "skip":
                return False
            elif on_conflict == "error":
                raise ValueError(f"Agent already exists: {agent_id}")

        await self.db.execute(
            """
            INSERT OR REPLACE INTO agents (
                id, name, description, system_prompt, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["name"],
                record.get("description"),
                record.get("system_prompt"),
                record.get("metadata", "{}"),
                record["created_at"],
            ),
        )

        return True

    async def _import_message(self, record: dict, on_conflict: str) -> bool:
        """Import a message record."""
        message_id = record["id"]

        # Check if exists
        cursor = await self.db.execute(
            "SELECT id FROM messages WHERE id = ?", (message_id,)
        )
        existing = await cursor.fetchone()

        if existing:
            if on_conflict == "skip":
                return False
            elif on_conflict == "error":
                raise ValueError(f"Message already exists: {message_id}")

        await self.db.execute(
            """
            INSERT OR REPLACE INTO messages (
                id, agent_id, sender_id, role, content, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["agent_id"],
                record.get("sender_id"),
                record["role"],
                record["content"],
                record.get("metadata", "{}"),
                record["created_at"],
            ),
        )

        return True

    async def _import_link(self, record: dict, on_conflict: str) -> bool:
        """Import a memory link record."""
        link_id = record["id"]
        source_id = record["source_id"]
        target_id = record["target_id"]
        link_type = record["link_type"]

        # Check if link exists by UNIQUE constraint (source_id, target_id, link_type)
        cursor = await self.db.execute(
            """
            SELECT id FROM memory_links
            WHERE source_id = ? AND target_id = ? AND link_type = ?
            """,
            (source_id, target_id, link_type),
        )
        existing = await cursor.fetchone()

        if existing:
            if on_conflict == "skip":
                return False
            elif on_conflict == "error":
                raise ValueError(
                    f"Link already exists: {source_id} -> {target_id} ({link_type})"
                )
            # on_conflict == "update" falls through to INSERT OR REPLACE

        # Use INSERT OR REPLACE only for update mode, otherwise INSERT
        if existing and on_conflict == "update":
            sql = """
                INSERT OR REPLACE INTO memory_links (
                    id, source_id, target_id, link_type, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """
        else:
            sql = """
                INSERT INTO memory_links (
                    id, source_id, target_id, link_type, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """

        await self.db.execute(
            sql,
            (
                link_id,
                source_id,
                target_id,
                link_type,
                record.get("metadata", "{}"),
                record["created_at"],
            ),
        )

        return True

    async def _import_decay_config(self, record: dict) -> bool:
        """Import decay config record."""
        await self.db.execute(
            """
            INSERT OR REPLACE INTO decay_config (
                id, enabled, threshold, grace_period_days,
                auto_run_interval_hours, max_delete_per_run,
                last_run_at, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("enabled", 0),
                record.get("threshold", 0.1),
                record.get("grace_period_days", 7),
                record.get("auto_run_interval_hours", 24),
                record.get("max_delete_per_run", 100),
                record.get("last_run_at"),
                record.get("updated_at"),
            ),
        )

        return True
