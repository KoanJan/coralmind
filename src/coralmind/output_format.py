# mypy: ignore-errors
"""
Output format utilities for dynamic model generation.

This module provides functions to dynamically generate Pydantic models
from format specifications (e.g., JSON Schema), enabling validation of
LLM outputs against user-defined schemas.
"""

import json
import logging
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model
from pydantic.functional_validators import AfterValidator

logger = logging.getLogger(__name__)


def json_schema_to_pydantic(schema: str | dict[str, Any], model_name: str = "DynamicModel") -> type[BaseModel]:
    """
    Convert a JSON Schema to a Pydantic model dynamically.

    Args:
        schema: JSON Schema as a string or dictionary
        model_name: Name for the generated model

    Returns:
        A Pydantic model class that validates against the schema

    Raises:
        ValueError: If the schema is invalid or unsupported
    """
    logger.debug(f"Converting JSON Schema to Pydantic model: model_name={model_name}")

    if isinstance(schema, str):
        try:
            schema_dict = json.loads(schema)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON Schema string: {e}")
            raise ValueError(f"Invalid JSON Schema string: {e}") from e
    else:
        schema_dict = schema

    model = _build_model(schema_dict, model_name)
    logger.debug(f"Pydantic model created successfully: {model_name}")
    return model


def _build_model(schema_dict: dict[str, Any], model_name: str = "DynamicModel") -> type[BaseModel]:
    """Build a Pydantic model from a JSON Schema dictionary."""
    if schema_dict.get("type") != "object" and "$ref" not in schema_dict:
        if "anyOf" in schema_dict or "oneOf" in schema_dict or "allOf" in schema_dict:
            pass
        else:
            raise ValueError("Only object type JSON Schemas are supported at the root level")

    defs = schema_dict.get("$defs", {})
    return _json_type_to_python(schema_dict, defs, model_name)


def _resolve_ref(ref: str, defs: dict[str, Any]) -> dict[str, Any]:
    """Resolve a $ref reference to its definition."""
    if not ref.startswith("#/"):
        raise ValueError(f"Only local references are supported: {ref}")

    parts = ref[2:].split("/")
    current: dict[str, Any] = {"$defs": defs}
    for part in parts:
        if part not in current:
            raise ValueError(f"Reference not found: {ref}")
        current = current[part]

    return current


def _json_type_to_python(
    type_def: dict[str, Any],
    defs: dict[str, Any],
    model_name: str = "DynamicModel"
) -> type[BaseModel]:
    """Convert a JSON Schema type definition to a Python type."""
    defs = defs or {}

    if "$ref" in type_def:
        resolved = _resolve_ref(type_def["$ref"], defs)
        return _json_type_to_python(resolved, defs, model_name)

    if "enum" in type_def:
        return _build_enum_type(type_def)

    if "const" in type_def:
        return _build_const_type(type_def)

    if "anyOf" in type_def:
        return _build_union_type(type_def, defs, "anyOf")

    if "oneOf" in type_def:
        return _build_union_type(type_def, defs, "oneOf")

    if "allOf" in type_def:
        return _build_all_of_type(type_def, defs)

    json_type = type_def.get("type")

    if json_type is None:
        return Any

    if isinstance(json_type, list):
        return _build_multi_type(json_type, type_def, defs)

    if json_type == "null":
        return type(None)

    if json_type == "array":
        return _build_array_type(type_def, defs)

    if json_type == "object":
        return _build_object_type(type_def, defs, model_name)

    type_mapping: dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
    }

    if json_type in type_mapping:
        base_type = type_mapping[json_type]
        return _apply_constraints(base_type, type_def)

    return Any


def _build_enum_type(type_def: dict[str, Any]) -> type:
    """Build an Enum type from JSON Schema enum."""
    enum_values = type_def["enum"]
    enum_name = type_def.get("title", "DynamicEnum")

    enum_dict = {str(v).upper().replace(" ", "_"): v for v in enum_values}
    return Enum(enum_name, enum_dict)


def _build_const_type(type_def: dict[str, Any]) -> type:
    """Build a Literal type from JSON Schema const."""
    const_value = type_def["const"]
    return Literal[const_value]


def _build_union_type(type_def: dict[str, Any], defs: dict[str, Any], key: str) -> type:
    """Build a Union type from JSON Schema anyOf/oneOf."""
    variants = type_def[key]
    types = [_json_type_to_python(v, defs) for v in variants]

    if len(types) == 1:
        return types[0]

    result = types[0]
    for t in types[1:]:
        result = result | t

    return result


def _build_all_of_type(type_def: dict[str, Any], defs: dict[str, Any]) -> type[BaseModel]:
    """Build a combined model from JSON Schema allOf."""
    schemas = type_def["allOf"]

    all_properties: dict[str, dict[str, Any]] = {}
    all_required: set[str] = set()

    for schema in schemas:
        resolved = schema
        if "$ref" in schema:
            resolved = _resolve_ref(schema["$ref"], defs)

        if "properties" in resolved:
            all_properties.update(resolved["properties"])
        if "required" in resolved:
            all_required.update(resolved["required"])

    fields: dict[str, Any] = {}
    for prop_name, prop_def in all_properties.items():
        field_type = _json_type_to_python(prop_def, defs)
        is_required = prop_name in all_required

        if is_required:
            fields[prop_name] = (field_type, ...)
        else:
            default = prop_def.get("default", None)
            fields[prop_name] = (field_type | None, Field(default=default))

    return create_model("AllOfModel", **fields)


def _build_multi_type(json_types: list[str], type_def: dict[str, Any], defs: dict[str, Any]) -> type:
    """Build a Union type from JSON Schema type array."""
    types = []
    for t in json_types:
        single_def = {**type_def, "type": t}
        types.append(_json_type_to_python(single_def, defs))

    if len(types) == 1:
        return types[0]

    result = types[0]
    for t in types[1:]:
        result = result | t

    return result


def _build_array_type(type_def: dict[str, Any], defs: dict[str, Any]) -> type:
    """Build a list type from JSON Schema array."""
    items_def = type_def.get("items", {})
    item_type = _json_type_to_python(items_def, defs)

    constraints = {}
    if "minItems" in type_def:
        constraints["min_length"] = type_def["minItems"]
    if "maxItems" in type_def:
        constraints["max_length"] = type_def["maxItems"]

    if constraints:
        return Annotated[list[item_type], Field(**constraints)]

    return list[item_type]


def _build_object_type(type_def: dict[str, Any], defs: dict[str, Any], model_name: str) -> type[BaseModel]:
    """Build a Pydantic model from JSON Schema object."""
    properties = type_def.get("properties", {})
    required = set(type_def.get("required", []))
    additional_props = type_def.get("additionalProperties", True)

    fields: dict[str, Any] = {}
    for prop_name, prop_def in properties.items():
        field_type = _json_type_to_python(prop_def, defs)
        is_required = prop_name in required

        if is_required:
            fields[prop_name] = (field_type, ...)
        else:
            default = prop_def.get("default", None)
            fields[prop_name] = (field_type | None, Field(default=default))

    model_config = {}
    if additional_props is False:
        model_config["extra"] = "forbid"
    elif isinstance(additional_props, dict):
        pass

    if model_config:
        model = create_model(model_name, __config__=ConfigDict(**model_config), **fields)
    else:
        model = create_model(model_name, **fields)

    return model


def _apply_constraints(base_type: type, type_def: dict[str, Any]) -> type:
    """Apply JSON Schema constraints to a base type."""
    constraints = {}

    if base_type is str:
        if "minLength" in type_def:
            constraints["min_length"] = type_def["minLength"]
        if "maxLength" in type_def:
            constraints["max_length"] = type_def["maxLength"]
        if "pattern" in type_def:
            pattern = type_def["pattern"]
            constraints["pattern"] = pattern
        if "format" in type_def:
            format_type = type_def["format"]
            if format_type in ("email", "uri", "date", "date-time", "uuid"):
                constraints["format"] = format_type

    elif base_type in (int, float):
        if "minimum" in type_def:
            constraints["ge"] = type_def["minimum"]
        if "maximum" in type_def:
            constraints["le"] = type_def["maximum"]
        if "exclusiveMinimum" in type_def:
            constraints["gt"] = type_def["exclusiveMinimum"]
        if "exclusiveMaximum" in type_def:
            constraints["lt"] = type_def["exclusiveMaximum"]
        if "multipleOf" in type_def:
            multiple = type_def["multipleOf"]
            if base_type is int:

                def validate_multiple(v: int) -> int:
                    if v % multiple != 0:
                        raise ValueError(f"Value must be a multiple of {multiple}")
                    return v

                return Annotated[int, AfterValidator(validate_multiple)]
            else:

                def validate_multiple_float(v: float) -> float:
                    if abs(v % multiple) > 1e-10:
                        raise ValueError(f"Value must be a multiple of {multiple}")
                    return v

                return Annotated[float, AfterValidator(validate_multiple_float)]

    if constraints:
        return Annotated[base_type, Field(**constraints)]

    return base_type
