"""Database connection and migration management."""

import asyncio
import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
import sqlite_vec

# Check if SQLite supports extension loading
# Apple's SQLite on some systems is built with OMIT_LOAD_EXTENSION
_SQLITE_SUPPORTS_EXTENSIONS = hasattr(sqlite3.Connection, 'enable_load_extension')

if not _SQLITE_SUPPORTS_EXTENSIONS:
    # Try to use pysqlite3 which is built against Homebrew SQLite
    try:
        import pysqlite3.dbapi2
        # Replace sqlite3 module globally for aiosqlite
        aiosqlite.core.sqlite3 = pysqlite3.dbapi2
        # Also update Row references for compatibility
        import sys
        sys.modules['sqlite3'] = pysqlite3.dbapi2
        _SQLITE_SUPPORTS_EXTENSIONS = True
    except ImportError as e:
        raise RuntimeError(
            "SQLite does not support extension loading. "
            "On macOS with Python 3.14+, install pysqlite3: "
            "LDFLAGS='-L/opt/homebrew/opt/sqlite/lib' "
            "CPPFLAGS='-I/opt/homebrew/opt/sqlite/include' pip install pysqlite3"
        ) from e


class Database:
    """Database connection and operations manager."""

    def __init__(self, database_path: str, embedding_dimensions: int = 384) -> None:
        """Initialize database manager.

        Args:
            database_path: Path to SQLite database file
            embedding_dimensions: Dimension of embedding vectors
        """
        self.database_path = database_path
        self.embedding_dimensions = embedding_dimensions
        self.conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()
        self._in_transaction = False

    async def connect(self) -> None:
        """Connect to database and load sqlite-vec extension."""
        # Ensure data directory exists
        db_dir = Path(self.database_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.conn = await aiosqlite.connect(self.database_path)
        # Use the sqlite3 module's Row factory (works with both stdlib and pysqlite3)
        self.conn.row_factory = aiosqlite.core.sqlite3.Row

        # Enable load_extension and load sqlite-vec
        await self.conn.enable_load_extension(True)

        # Load sqlite-vec in aiosqlite's internal thread to avoid threading issues.
        # aiosqlite runs sqlite operations in a separate thread, so we must use
        # _execute() to run sqlite_vec.load() in that same thread context.
        # Note: _execute() is a semi-private API but is the only way to ensure
        # thread-safe extension loading with aiosqlite.
        def _load_sqlite_vec(connection: object) -> None:
            sqlite_vec.load(connection)  # type: ignore[arg-type]

        await self.conn._execute(_load_sqlite_vec, self.conn._conn)

        await self.conn.enable_load_extension(False)

        # Enable foreign keys
        await self.conn.execute("PRAGMA foreign_keys = ON")

    async def close(self) -> None:
        """Close database connection."""
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def execute(
        self, sql: str, parameters: tuple[Any, ...] | dict[str, Any] = ()
    ) -> aiosqlite.Cursor:
        """Execute a SQL statement.

        Args:
            sql: SQL statement
            parameters: Query parameters

        Returns:
            Database cursor
        """
        if not self.conn:
            raise RuntimeError("Database not connected")
        return await self.conn.execute(sql, parameters)

    async def executemany(self, sql: str, parameters: list[tuple[Any, ...]]) -> None:
        """Execute a SQL statement with multiple parameter sets.

        Args:
            sql: SQL statement
            parameters: List of parameter tuples
        """
        if not self.conn:
            raise RuntimeError("Database not connected")
        await self.conn.executemany(sql, parameters)

    async def commit(self) -> None:
        """Commit current transaction."""
        if not self.conn:
            raise RuntimeError("Database not connected")
        await self.conn.commit()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Context manager for database transactions.

        Provides exclusive write access with proper nesting detection.
        If already in a transaction, yields without starting a new one
        to prevent "cannot start a transaction within a transaction" errors.

        Yields:
            None

        Example:
            async with db.transaction():
                await db.execute(...)
        """
        if not self.conn:
            raise RuntimeError("Database not connected")

        # If already in a transaction, just yield without nesting
        if self._in_transaction:
            yield
            return

        # Acquire write lock for exclusive access
        async with self._write_lock:
            self._in_transaction = True
            await self.conn.execute("BEGIN")
            try:
                yield
                await self.conn.commit()
            except Exception:
                await self.conn.rollback()
                raise
            finally:
                self._in_transaction = False

    async def migrate(self) -> None:
        """Run database migrations."""
        # Check current schema version
        try:
            cursor = await self.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            current_version = row[0] if row else 0
        except (aiosqlite.OperationalError, aiosqlite.core.sqlite3.OperationalError):
            current_version = 0

        # Run migrations if needed
        if current_version < 1:
            await self._migrate_v1()

        if current_version < 2:
            await self._migrate_v2()

        if current_version < 3:
            await self._migrate_v3()

        if current_version < 4:
            await self._migrate_v4()

    async def _migrate_v1(self) -> None:
        """Initial database schema migration."""
        async with self.transaction():
            # Create schema_version table
            await self.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at DATETIME NOT NULL
                )
            """)

            # Create agents table
            await self.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at DATETIME NOT NULL,
                    last_active_at DATETIME NOT NULL
                )
            """)

            # Create memories table
            await self.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    content_type TEXT NOT NULL DEFAULT 'text',
                    memory_tier TEXT NOT NULL DEFAULT 'long_term',
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    agent_id TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    expires_at DATETIME,
                    FOREIGN KEY (agent_id) REFERENCES agents(id)
                )
            """)

            # Create indexes for memories
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_tier ON memories(memory_tier)"
            )
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent_id)"
            )
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)"
            )
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_expires ON memories(expires_at) "
                "WHERE expires_at IS NOT NULL"
            )

            # Create embeddings virtual table with cosine distance metric
            await self.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
                    memory_id TEXT PRIMARY KEY,
                    embedding FLOAT[{self.embedding_dimensions}] distance_metric=cosine
                )
            """)

            # Create messages table
            await self.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    sender_id TEXT NOT NULL,
                    receiver_id TEXT,
                    content TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    metadata TEXT DEFAULT '{}',
                    created_at DATETIME NOT NULL,
                    read_at DATETIME,
                    FOREIGN KEY (sender_id) REFERENCES agents(id),
                    FOREIGN KEY (receiver_id) REFERENCES agents(id)
                )
            """)

            # Create indexes for messages
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_receiver "
                "ON messages(receiver_id, status)"
            )
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)"
            )

            # Create shared_contexts table
            await self.execute("""
                CREATE TABLE IF NOT EXISTS shared_contexts (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    owner_agent_id TEXT NOT NULL,
                    access_level TEXT DEFAULT 'public',
                    allowed_agents TEXT DEFAULT '[]',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY (owner_agent_id) REFERENCES agents(id)
                )
            """)

            # Create knowledge_documents table
            await self.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT,
                    category TEXT,
                    version INTEGER DEFAULT 1,
                    metadata TEXT DEFAULT '{}',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """)

            # Create knowledge_chunks table
            await self.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
                )
            """)

            # Create index for chunks
            await self.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_document "
                "ON knowledge_chunks(document_id, chunk_index)"
            )

            # Create chunk_embeddings virtual table with cosine distance metric
            await self.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
                    chunk_id TEXT PRIMARY KEY,
                    embedding FLOAT[{self.embedding_dimensions}] distance_metric=cosine
                )
            """)

            # Record migration
            await self.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (1, datetime.now(timezone.utc).isoformat()),
            )

    async def _migrate_v2(self) -> None:
        """v1.1.0 feature migration (v1 -> v2)."""
        async with self.transaction():
            # 1. Add importance scoring columns to memories
            await self.execute("""
                ALTER TABLE memories
                ADD COLUMN importance_score FLOAT DEFAULT 0.5
            """)

            await self.execute("""
                ALTER TABLE memories
                ADD COLUMN access_count INTEGER DEFAULT 0
            """)

            await self.execute("""
                ALTER TABLE memories
                ADD COLUMN last_accessed_at DATETIME
            """)

            # 2. Add consolidation column
            await self.execute("""
                ALTER TABLE memories
                ADD COLUMN consolidated_from TEXT DEFAULT NULL
            """)

            # 3. Create access log table
            await self.execute("""
                CREATE TABLE memory_access_log (
                    id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    accessed_at DATETIME NOT NULL,
                    access_type TEXT NOT NULL,
                    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
                )
            """)

            await self.execute("""
                CREATE INDEX idx_access_log_memory
                ON memory_access_log(memory_id, accessed_at DESC)
            """)

            # 4. Create FTS5 table
            await self.execute("""
                CREATE VIRTUAL TABLE memories_fts USING fts5(
                    content,
                    content_id UNINDEXED,
                    tokenize='unicode61'
                )
            """)

            # 5. Populate FTS5 from existing memories
            await self.execute("""
                INSERT INTO memories_fts (content, content_id)
                SELECT content, id FROM memories
            """)

            # 6. Create FTS5 sync triggers
            await self.execute("""
                CREATE TRIGGER memories_fts_insert AFTER INSERT ON memories
                BEGIN
                    INSERT INTO memories_fts (content, content_id)
                    VALUES (NEW.content, NEW.id);
                END
            """)

            await self.execute("""
                CREATE TRIGGER memories_fts_update AFTER UPDATE OF content ON memories
                BEGIN
                    UPDATE memories_fts SET content = NEW.content
                    WHERE content_id = NEW.id;
                END
            """)

            await self.execute("""
                CREATE TRIGGER memories_fts_delete AFTER DELETE ON memories
                BEGIN
                    DELETE FROM memories_fts WHERE content_id = OLD.id;
                END
            """)

            # 7. Record migration version
            await self.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (2, datetime.now(timezone.utc).isoformat()),
            )

    async def _migrate_v3(self) -> None:
        """v1.2.0 feature migration (v2 -> v3)."""
        async with self.transaction():
            # 1. Create memory_links table
            await self.execute("""
                CREATE TABLE memory_links (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    link_type TEXT NOT NULL DEFAULT 'related',
                    metadata TEXT DEFAULT '{}',
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES memories(id) ON DELETE CASCADE,
                    FOREIGN KEY (target_id) REFERENCES memories(id) ON DELETE CASCADE,
                    UNIQUE(source_id, target_id, link_type)
                )
            """)

            # 2. Create indexes for memory_links
            await self.execute("""
                CREATE INDEX idx_links_source ON memory_links(source_id)
            """)

            await self.execute("""
                CREATE INDEX idx_links_target ON memory_links(target_id)
            """)

            await self.execute("""
                CREATE INDEX idx_links_type ON memory_links(link_type)
            """)

            # 3. Create decay_config table
            await self.execute("""
                CREATE TABLE decay_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    enabled INTEGER DEFAULT 0,
                    threshold REAL DEFAULT 0.1,
                    grace_period_days INTEGER DEFAULT 7,
                    auto_run_interval_hours INTEGER DEFAULT 24,
                    max_delete_per_run INTEGER DEFAULT 100,
                    last_run_at DATETIME,
                    updated_at DATETIME NOT NULL
                )
            """)

            # 4. Create decay_log table
            await self.execute("""
                CREATE TABLE decay_log (
                    id TEXT PRIMARY KEY,
                    run_at DATETIME NOT NULL,
                    deleted_count INTEGER NOT NULL,
                    deleted_ids TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    dry_run INTEGER NOT NULL
                )
            """)

            # 5. Add smart chunking columns to knowledge_chunks
            await self.execute("""
                ALTER TABLE knowledge_chunks
                ADD COLUMN section_path TEXT DEFAULT '[]'
            """)

            await self.execute("""
                ALTER TABLE knowledge_chunks
                ADD COLUMN has_previous INTEGER DEFAULT 0
            """)

            await self.execute("""
                ALTER TABLE knowledge_chunks
                ADD COLUMN has_next INTEGER DEFAULT 0
            """)

            # 6. Create performance index for decay
            await self.execute("""
                CREATE INDEX idx_memories_importance
                ON memories(importance_score, created_at)
            """)

            # 7. Update messages table schema if needed (add missing columns from v1.1.0)
            # Check if columns exist first
            cursor = await self.execute("PRAGMA table_info(messages)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            if "agent_id" not in column_names:
                await self.execute("""
                    ALTER TABLE messages
                    ADD COLUMN agent_id TEXT
                """)

            if "role" not in column_names:
                await self.execute("""
                    ALTER TABLE messages
                    ADD COLUMN role TEXT DEFAULT 'user'
                """)

            # Add system_prompt column to agents if missing
            cursor = await self.execute("PRAGMA table_info(agents)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            if "system_prompt" not in column_names:
                await self.execute("""
                    ALTER TABLE agents
                    ADD COLUMN system_prompt TEXT
                """)

            # 8. Record migration version
            await self.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (3, datetime.now(timezone.utc).isoformat()),
            )

    async def _migrate_v4(self) -> None:
        """v1.3.0 migration: Switch to cosine distance for vector search.

        Recreates embeddings and chunk_embeddings virtual tables with
        distance_metric=cosine for more accurate semantic similarity scores.
        """
        async with self.transaction():
            # 1. Backup embeddings data to temporary table
            await self.execute("""
                CREATE TABLE embeddings_backup AS
                SELECT memory_id, embedding FROM embeddings
            """)

            # 2. Drop old embeddings virtual table
            await self.execute("DROP TABLE embeddings")

            # 3. Create new embeddings table with cosine distance metric
            await self.execute(f"""
                CREATE VIRTUAL TABLE embeddings USING vec0(
                    memory_id TEXT PRIMARY KEY,
                    embedding FLOAT[{self.embedding_dimensions}] distance_metric=cosine
                )
            """)

            # 4. Restore embeddings data
            await self.execute("""
                INSERT INTO embeddings (memory_id, embedding)
                SELECT memory_id, embedding FROM embeddings_backup
            """)

            # 5. Drop backup table
            await self.execute("DROP TABLE embeddings_backup")

            # 6. Do the same for chunk_embeddings
            await self.execute("""
                CREATE TABLE chunk_embeddings_backup AS
                SELECT chunk_id, embedding FROM chunk_embeddings
            """)

            await self.execute("DROP TABLE chunk_embeddings")

            await self.execute(f"""
                CREATE VIRTUAL TABLE chunk_embeddings USING vec0(
                    chunk_id TEXT PRIMARY KEY,
                    embedding FLOAT[{self.embedding_dimensions}] distance_metric=cosine
                )
            """)

            await self.execute("""
                INSERT INTO chunk_embeddings (chunk_id, embedding)
                SELECT chunk_id, embedding FROM chunk_embeddings_backup
            """)

            await self.execute("DROP TABLE chunk_embeddings_backup")

            # 7. Record migration version
            await self.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (4, datetime.now(timezone.utc).isoformat()),
            )

    @staticmethod
    def serialize_json(data: Any) -> str:
        """Serialize data to JSON string.

        Args:
            data: Data to serialize

        Returns:
            JSON string
        """
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def deserialize_json(data: str) -> Any:
        """Deserialize JSON string to data.

        Args:
            data: JSON string

        Returns:
            Deserialized data
        """
        return json.loads(data) if data else {}
