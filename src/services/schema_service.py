"""Service for memory schema management."""

import json
import re
from datetime import datetime
from typing import Any

from src.db.database import Database
from src.exceptions import ConflictError, ValidationError
from src.models.schema import FieldType, MemorySchema, SchemaField
from src.services.namespace_service import NamespaceService


class SchemaService:
    """Service for managing memory schemas."""

    SCHEMA_NAME_PATTERN = r"^[a-zA-Z0-9_]{1,128}$"

    def __init__(
        self, db: Database, namespace_service: NamespaceService
    ) -> None:
        """Initialize schema service.

        Args:
            db: Database instance
            namespace_service: Namespace service
        """
        self.db = db
        self.namespace_service = namespace_service

    async def register_schema(
        self,
        name: str,
        namespace: str,
        fields: list[SchemaField],
        description: str | None = None,
    ) -> MemorySchema:
        """Register a new memory schema.

        Args:
            name: Schema name (unique within namespace)
            namespace: Target namespace
            fields: Field definitions
            description: Optional schema description

        Returns:
            Created MemorySchema

        Raises:
            ValidationError: If schema definition is invalid
            ConflictError: If schema already exists
        """
        # Validate schema name
        if not re.match(self.SCHEMA_NAME_PATTERN, name):
            raise ValidationError(
                f"Invalid schema name: {name}. "
                "Must be 1-128 alphanumeric characters or underscores."
            )

        # Validate fields
        if fields:
            field_names = set()
            for field in fields:
                if field.name in field_names:
                    raise ValidationError(f"Duplicate field name: {field.name}")
                field_names.add(field.name)

                # Validate field name
                if not re.match(r"^[a-zA-Z0-9_]{1,64}$", field.name):
                    raise ValidationError(
                        f"Invalid field name: {field.name}. "
                        "Must be 1-64 alphanumeric characters or underscores."
                    )

        # Check if schema already exists
        existing = await self.get_schema(namespace, name, version=None)
        if existing:
            raise ConflictError(
                f"Schema '{name}' already exists in namespace '{namespace}'"
            )

        # Create schema
        schema = MemorySchema(
            name=name,
            namespace=namespace,
            version=1,
            fields=fields,
        )

        # Insert into database
        await self.db.execute(
            """
            INSERT INTO memory_schemas (
                id, name, namespace, version, fields, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                schema.id,
                schema.name,
                schema.namespace,
                schema.version,
                json.dumps([field.model_dump() for field in schema.fields]),
                schema.created_at.isoformat(),
                schema.updated_at.isoformat(),
            ),
        )
        await self.db.commit()

        return schema

    async def get_schema_by_id(
        self,
        schema_id: str,
    ) -> MemorySchema | None:
        """Get a schema by ID.

        Args:
            schema_id: Schema ID

        Returns:
            MemorySchema or None if not found
        """
        cursor = await self.db.execute(
            """
            SELECT id, name, namespace, version, fields, created_at, updated_at
            FROM memory_schemas
            WHERE id = ?
            """,
            (schema_id,),
        )

        row = await cursor.fetchone()
        if not row:
            return None

        row_dict = dict(row)
        fields_data = json.loads(row_dict["fields"])
        fields = [SchemaField(**field_data) for field_data in fields_data]

        return MemorySchema(
            id=row_dict["id"],
            name=row_dict["name"],
            namespace=row_dict["namespace"],
            version=row_dict["version"],
            fields=fields,
            created_at=datetime.fromisoformat(row_dict["created_at"]),
            updated_at=datetime.fromisoformat(row_dict["updated_at"]),
        )

    async def get_schema(
        self,
        namespace: str,
        name: str,
        version: int | None = None,
    ) -> MemorySchema | None:
        """Get a specific schema.

        Args:
            namespace: Target namespace
            name: Schema name
            version: Specific version (None for latest)

        Returns:
            MemorySchema or None if not found
        """
        if version is not None:
            # Get specific version
            cursor = await self.db.execute(
                """
                SELECT id, name, namespace, version, fields, created_at, updated_at
                FROM memory_schemas
                WHERE namespace = ? AND name = ? AND version = ?
                """,
                (namespace, name, version),
            )
        else:
            # Get latest version
            cursor = await self.db.execute(
                """
                SELECT id, name, namespace, version, fields, created_at, updated_at
                FROM memory_schemas
                WHERE namespace = ? AND name = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (namespace, name),
            )

        row = await cursor.fetchone()
        if not row:
            return None

        row_dict = dict(row)
        fields_data = json.loads(row_dict["fields"])
        fields = [SchemaField(**field_data) for field_data in fields_data]

        return MemorySchema(
            id=row_dict["id"],
            name=row_dict["name"],
            namespace=row_dict["namespace"],
            version=row_dict["version"],
            fields=fields,
            created_at=datetime.fromisoformat(row_dict["created_at"]),
            updated_at=datetime.fromisoformat(row_dict["updated_at"]),
        )

    async def list_schemas(
        self,
        namespace: str | None = None,
        include_fields: bool = False,
    ) -> list[MemorySchema]:
        """List registered schemas.

        Args:
            namespace: Target namespace (None for all)
            include_fields: Include field definitions

        Returns:
            List of MemorySchema objects
        """
        if namespace:
            cursor = await self.db.execute(
                """
                SELECT id, name, namespace, version, fields, created_at, updated_at
                FROM memory_schemas
                WHERE namespace = ?
                ORDER BY namespace, name, version DESC
                """,
                (namespace,),
            )
        else:
            cursor = await self.db.execute(
                """
                SELECT id, name, namespace, version, fields, created_at, updated_at
                FROM memory_schemas
                ORDER BY namespace, name, version DESC
                """
            )

        rows = await cursor.fetchall()

        schemas = []
        for row in rows:
            row_dict = dict(row)
            fields_data = json.loads(row_dict["fields"]) if include_fields else []
            fields = [SchemaField(**field_data) for field_data in fields_data]

            schema = MemorySchema(
                id=row_dict["id"],
                name=row_dict["name"],
                namespace=row_dict["namespace"],
                version=row_dict["version"],
                fields=fields,
                created_at=datetime.fromisoformat(row_dict["created_at"]),
                updated_at=datetime.fromisoformat(row_dict["updated_at"]),
            )
            schemas.append(schema)

        return schemas

    async def validate_data(
        self,
        schema: MemorySchema,
        data: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate data against a schema.

        Args:
            schema: Schema to validate against
            data: Data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check required fields
        for field in schema.fields:
            if field.required and field.name not in data:
                errors.append(f"Required field missing: {field.name}")

        # Validate each field
        for field in schema.fields:
            if field.name not in data:
                continue

            value = data[field.name]

            # Validate type
            is_valid, type_error = self._validate_type(field, value)
            if not is_valid:
                errors.append(type_error)
                continue

            # Apply validation rules
            if field.validation:
                validation_errors = self._apply_validation_rules(
                    field, value, field.validation
                )
                errors.extend(validation_errors)

        return (len(errors) == 0, errors)

    def _validate_type(
        self, field: SchemaField, value: Any
    ) -> tuple[bool, str]:
        """Validate value type matches field type.

        Args:
            field: Schema field
            value: Value to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            if field.required:
                return (False, f"Field '{field.name}' cannot be None")
            return (True, "")

        type_validators = {
            FieldType.STRING: lambda v: isinstance(v, str),
            FieldType.NUMBER: lambda v: isinstance(v, (int, float)),
            FieldType.BOOLEAN: lambda v: isinstance(v, bool),
            FieldType.DATETIME: lambda v: isinstance(v, str),  # ISO format string
            FieldType.ARRAY: lambda v: isinstance(v, list),
            FieldType.OBJECT: lambda v: isinstance(v, dict),
        }

        validator = type_validators.get(field.type)
        if not validator:
            return (False, f"Unknown field type: {field.type}")

        if not validator(value):
            return (
                False,
                f"Field '{field.name}' has invalid type. "
                f"Expected {field.type.value}, got {type(value).__name__}",
            )

        return (True, "")

    def _apply_validation_rules(
        self,
        field: SchemaField,
        value: Any,
        validation: dict[str, Any],
    ) -> list[str]:
        """Apply validation rules to a value.

        Args:
            field: Schema field
            value: Value to validate
            validation: Validation rules

        Returns:
            List of error messages
        """
        errors = []

        # Min/max for numbers
        if field.type == FieldType.NUMBER:
            if "min" in validation and value < validation["min"]:
                errors.append(
                    f"Field '{field.name}' must be >= {validation['min']}"
                )
            if "max" in validation and value > validation["max"]:
                errors.append(
                    f"Field '{field.name}' must be <= {validation['max']}"
                )

        # Min/max length for strings
        if field.type == FieldType.STRING:
            if "min" in validation and len(value) < validation["min"]:
                errors.append(
                    f"Field '{field.name}' must have length >= {validation['min']}"
                )
            if "max" in validation and len(value) > validation["max"]:
                errors.append(
                    f"Field '{field.name}' must have length <= {validation['max']}"
                )

        # Pattern for strings
        if field.type == FieldType.STRING and "pattern" in validation:
            pattern = validation["pattern"]
            if not re.match(pattern, value):
                errors.append(
                    f"Field '{field.name}' does not match pattern: {pattern}"
                )

        # Enum validation
        if "enum" in validation:
            if value not in validation["enum"]:
                errors.append(
                    f"Field '{field.name}' must be one of: {validation['enum']}"
                )

        return errors
