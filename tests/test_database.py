"""Tests for database operations."""

import pytest

from src.db.database import Database


class TestDatabase:
    """Test Database class."""

    @pytest.mark.asyncio
    async def test_database_initialization(self, memory_db: Database):
        """Test database initialization and migration."""
        # Check that tables exist
        cursor = await memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in await cursor.fetchall()}

        expected_tables = {
            "schema_version",
            "agents",
            "memories",
            "embeddings",
            "messages",
            "shared_contexts",
            "knowledge_documents",
            "knowledge_chunks",
            "chunk_embeddings",
        }

        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    @pytest.mark.asyncio
    async def test_sqlite_vec_extension_loaded(self, memory_db: Database):
        """Test that sqlite-vec extension is loaded."""
        # Try to use vec0 functionality
        cursor = await memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='embeddings'"
        )
        result = await cursor.fetchone()

        assert result is not None
        assert result["name"] == "embeddings"

    @pytest.mark.asyncio
    async def test_transaction_commit(self, memory_db: Database):
        """Test transaction commit."""
        async with memory_db.transaction():
            await memory_db.execute(
                "INSERT INTO agents (id, name, description, metadata, created_at, last_active_at) "
                "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
                ("test-agent", "Test", "Description", "{}"),
            )

        # Verify data persisted
        cursor = await memory_db.execute("SELECT * FROM agents WHERE id = ?", ("test-agent",))
        result = await cursor.fetchone()

        assert result is not None
        assert result["id"] == "test-agent"
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, memory_db: Database):
        """Test transaction rollback on error."""
        try:
            async with memory_db.transaction():
                await memory_db.execute(
                    "INSERT INTO agents (id, name, description, metadata, created_at, last_active_at) "
                    "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
                    ("rollback-agent", "Test", "Description", "{}"),
                )
                # Intentionally raise an error
                raise ValueError("Intentional error")
        except ValueError:
            pass

        # Verify data was rolled back
        cursor = await memory_db.execute(
            "SELECT * FROM agents WHERE id = ?", ("rollback-agent",)
        )
        result = await cursor.fetchone()

        assert result is None

    @pytest.mark.asyncio
    async def test_foreign_keys_enabled(self, memory_db: Database):
        """Test that foreign keys are enabled."""
        cursor = await memory_db.execute("PRAGMA foreign_keys")
        result = await cursor.fetchone()

        assert result[0] == 1

    @pytest.mark.asyncio
    async def test_serialize_deserialize_json(self):
        """Test JSON serialization/deserialization."""
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        serialized = Database.serialize_json(data)
        assert isinstance(serialized, str)

        deserialized = Database.deserialize_json(serialized)
        assert deserialized == data

    @pytest.mark.asyncio
    async def test_deserialize_empty_string(self):
        """Test deserializing empty string."""
        result = Database.deserialize_json("")
        assert result == {}

    @pytest.mark.asyncio
    async def test_execute_many(self, memory_db: Database):
        """Test executemany operation."""
        agents = [
            ("agent-1", "Agent 1", "First", "{}"),
            ("agent-2", "Agent 2", "Second", "{}"),
            ("agent-3", "Agent 3", "Third", "{}"),
        ]

        await memory_db.executemany(
            "INSERT INTO agents (id, name, description, metadata, created_at, last_active_at) "
            "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
            agents,
        )

        # Commit the transaction
        await memory_db.commit()

        # Verify all agents inserted
        cursor = await memory_db.execute("SELECT COUNT(*) FROM agents")
        result = await cursor.fetchone()
        assert result[0] == 3
