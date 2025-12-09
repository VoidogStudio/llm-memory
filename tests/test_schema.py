"""Tests for Structured Memory Schema (FR-002)."""

import pytest
from src.exceptions import NotFoundError, ValidationError, ConflictError
from src.models.schema import FieldType, SchemaField, MemorySchema
from src.services.schema_service import SchemaService


class TestSchemaRegistration:
    """Test schema registration."""

    async def test_basic_schema_registration(self, schema_service):
        """SCH-001: Test basic schema registration."""
        # Given: Valid field definition
        fields = [
            SchemaField(name="status", type=FieldType.STRING, required=True),
            SchemaField(name="priority", type=FieldType.NUMBER, required=False),
        ]

        # When: Register schema
        schema = await schema_service.register_schema(
            name="task", namespace="default", fields=fields
        )

        # Then: Schema created
        assert schema.name == "task"
        assert schema.version == 1
        assert len(schema.fields) == 2
        assert schema.fields[0].name == "status"

    async def test_duplicate_schema_registration(self, schema_service):
        """SCH-002: Test duplicate schema registration."""
        # Given: Existing "task" schema
        fields = [SchemaField(name="status", type=FieldType.STRING, required=True)]
        await schema_service.register_schema(
            name="task", namespace="default", fields=fields
        )

        # When/Then: Duplicate registration raises ConflictError
        with pytest.raises(ConflictError):
            await schema_service.register_schema(
                name="task", namespace="default", fields=fields
            )

    async def test_invalid_field_type(self, schema_service):
        """SCH-003: Test invalid field type."""
        # Given: Invalid field type
        # When/Then: Creating field with invalid type raises ValueError
        with pytest.raises(ValueError):
            SchemaField(name="foo", type="invalid_type", required=False)

    async def test_validation_rules(self, schema_service):
        """SCH-004: Test validation rules in fields."""
        # Given: Field with validation rules
        fields = [
            SchemaField(
                name="score",
                type=FieldType.NUMBER,
                required=False,
                validation={"min": 0, "max": 100},
            )
        ]

        # When: Register schema
        schema = await schema_service.register_schema(
            name="grade", namespace="default", fields=fields
        )

        # Then: Schema created with validation
        assert schema.fields[0].validation == {"min": 0, "max": 100}


class TestSchemaRetrieval:
    """Test schema retrieval."""

    async def test_list_schemas(self, schema_service):
        """SCH-005: Test schema list retrieval."""
        # Given: 3 registered schemas
        await schema_service.register_schema(
            name="task",
            namespace="default",
            fields=[SchemaField(name="s", type=FieldType.STRING, required=False)],
        )
        await schema_service.register_schema(
            name="note",
            namespace="default",
            fields=[SchemaField(name="t", type=FieldType.STRING, required=False)],
        )
        await schema_service.register_schema(
            name="event",
            namespace="default",
            fields=[SchemaField(name="d", type=FieldType.DATETIME, required=False)],
        )

        # When: List schemas
        schemas = await schema_service.list_schemas(namespace="default")

        # Then: 3 schemas returned
        assert len(schemas) == 3
        schema_names = {s.name for s in schemas}
        assert schema_names == {"task", "note", "event"}

    async def test_get_specific_schema(self, schema_service):
        """SCH-006: Test specific schema retrieval."""
        # Given: "task" schema exists
        await schema_service.register_schema(
            name="task",
            namespace="default",
            fields=[SchemaField(name="status", type=FieldType.STRING, required=True)],
        )

        # When: Get schema
        schema = await schema_service.get_schema(name="task", namespace="default")

        # Then: Complete schema returned
        assert schema.name == "task"
        assert len(schema.fields) == 1
        assert schema.fields[0].name == "status"

    async def test_get_nonexistent_schema(self, schema_service):
        """SCH-007: Test non-existent schema retrieval."""
        # When: Get unknown schema
        schema = await schema_service.get_schema(name="unknown", namespace="default")

        # Then: Returns None
        assert schema is None


class TestTypedMemoryStore:
    """Test typed memory storage."""

    async def test_normal_typed_memory_store(
        self, memory_service, schema_service, sample_schema
    ):
        """SCH-008: Test normal typed memory storage."""
        # Given: "task" schema with status (required) and priority (optional)
        # sample_schema already created in fixture

        # When: Store typed memory
        memory = await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active", "priority": 5},
        )

        # Then: Memory created with schema
        assert memory.schema_id is not None
        assert memory.structured_content == {"status": "active", "priority": 5}
        assert memory.content is not None  # Auto-generated

    async def test_missing_required_field(self, memory_service, sample_schema):
        """SCH-009: Test missing required field."""
        # Given: "task" schema with required status field
        # When/Then: Missing required field raises ValidationError
        with pytest.raises(ValidationError, match="status"):
            await memory_service.store_typed(
                schema_id=sample_schema.id,
                namespace="default",
                structured_content={"priority": 5},  # Missing status
            )

    async def test_type_mismatch(self, memory_service, sample_schema):
        """SCH-010: Test type mismatch validation."""
        # Given: "task" schema with priority as number
        # When/Then: String value for number field raises ValidationError
        with pytest.raises(ValidationError, match="priority"):
            await memory_service.store_typed(
                schema_id=sample_schema.id,
                namespace="default",
                structured_content={"status": "ok", "priority": "high"},  # Wrong type
            )

    async def test_custom_content(self, memory_service, sample_schema):
        """SCH-011: Test custom content specification."""
        # Given: "task" schema
        # When: Store with custom content
        memory = await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active"},
            content="Custom description",
        )

        # Then: Custom content used
        assert memory.content == "Custom description"

    async def test_validation_rule_violation(self, schema_service, memory_service):
        """SCH-012: Test validation rule violation."""
        # Given: Schema with score validation (0-100)
        schema = await schema_service.register_schema(
            name="grade",
            namespace="default",
            fields=[
                SchemaField(
                    name="score",
                    type=FieldType.NUMBER,
                    required=True,
                    validation={"min": 0, "max": 100},
                )
            ],
        )

        # When/Then: Value outside range raises ValidationError
        with pytest.raises(ValidationError):
            await memory_service.store_typed(
                schema_id=schema.id,
                namespace="default",
                structured_content={"score": 150},  # Exceeds max
            )


class TestTypedMemorySearch:
    """Test typed memory search."""

    async def test_single_field_search(self, memory_service, sample_schema):
        """SCH-013: Test single field condition search."""
        # Given: Multiple task memories with different status
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active", "priority": 1},
        )
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "completed", "priority": 2},
        )
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active", "priority": 3},
        )

        # When: Search for active tasks
        results = await memory_service.search_typed(
            schema_id=sample_schema.id, namespace="default", field_conditions={"status": "active"}
        )

        # Then: 2 active tasks returned
        assert len(results) == 2
        for mem in results:
            assert mem.structured_content["status"] == "active"

    async def test_multiple_field_search(self, memory_service, sample_schema):
        """SCH-014: Test multiple field conditions search."""
        # Given: Multiple tasks
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active", "priority": 5},
        )
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active", "priority": 3},
        )
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "completed", "priority": 5},
        )

        # When: Search with multiple conditions
        results = await memory_service.search_typed(
            schema_id=sample_schema.id,
            namespace="default",
            field_conditions={"status": "active", "priority": 5},
        )

        # Then: Only memories matching both conditions
        assert len(results) == 1
        assert results[0].structured_content["status"] == "active"
        assert results[0].structured_content["priority"] == 5

    async def test_comparison_operator_search(self, memory_service, sample_schema):
        """SCH-015: Test comparison operator search."""
        # Given: Tasks with different priorities
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active", "priority": 1},
        )
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active", "priority": 5},
        )
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active", "priority": 10},
        )

        # When: Search with >= operator
        results = await memory_service.search_typed(
            schema_id=sample_schema.id,
            namespace="default",
            field_conditions={"priority": {"$gte": 5}},
        )

        # Then: Priorities >= 5
        assert len(results) == 2
        priorities = {m.structured_content["priority"] for m in results}
        assert priorities == {5, 10}

    async def test_empty_search_results(self, memory_service, sample_schema):
        """SCH-016: Test search with no results."""
        # Given: Only active tasks
        await memory_service.store_typed(
            schema_id=sample_schema.id,
            namespace="default",
            structured_content={"status": "active", "priority": 1},
        )

        # When: Search for archived
        results = await memory_service.search_typed(
            schema_id=sample_schema.id,
            namespace="default",
            field_conditions={"status": "archived"},
        )

        # Then: Empty list
        assert len(results) == 0


# Fixtures

@pytest.fixture
async def schema_service(memory_db, namespace_service):
    """SchemaService instance for testing."""
    return SchemaService(db=memory_db, namespace_service=namespace_service)


@pytest.fixture
async def sample_schema(schema_service):
    """Create a sample task schema for testing."""
    return await schema_service.register_schema(
        name="task",
        namespace="default",
        fields=[
            SchemaField(name="status", type=FieldType.STRING, required=True),
            SchemaField(name="priority", type=FieldType.NUMBER, required=False),
            SchemaField(name="due_date", type=FieldType.DATETIME, required=False),
        ],
    )
