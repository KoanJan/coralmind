import pytest
from pydantic import ValidationError

from coralmind.output_format import json_schema_to_pydantic


class TestBasicTypes:

    def test_simple_string_field(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="test")
        assert instance.name == "test"

    def test_multiple_field_types(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"}
            },
            "required": ["name", "age"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="test", age=25, score=99.5, active=True)
        assert instance.name == "test"
        assert instance.age == 25
        assert instance.score == 99.5
        assert instance.active is True

    def test_optional_field(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "nickname": {"type": "string"}
            },
            "required": ["name"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="test")
        assert instance.name == "test"
        assert instance.nickname is None

    def test_field_with_default(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "status": {"type": "string", "default": "active"}
            },
            "required": ["name"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="test")
        assert instance.name == "test"
        assert instance.status == "active"


class TestArrayType:

    def test_array_of_strings(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["tags"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(tags=["a", "b", "c"])
        assert instance.tags == ["a", "b", "c"]

    def test_array_min_items(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2
                }
            },
            "required": ["items"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(items=["a", "b"])
        assert instance.items == ["a", "b"]
        with pytest.raises(ValidationError):
            model_cls(items=["a"])

    def test_array_max_items(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 2
                }
            },
            "required": ["items"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(items=["a", "b"])
        assert instance.items == ["a", "b"]
        with pytest.raises(ValidationError):
            model_cls(items=["a", "b", "c"])


class TestNestedObject:

    def test_nested_object(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    },
                    "required": ["name"]
                }
            },
            "required": ["user"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(user={"name": "test", "email": "test@example.com"})
        assert instance.user.name == "test"
        assert instance.user.email == "test@example.com"

    def test_deeply_nested_object(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "company": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "address": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                                "country": {"type": "string"}
                            },
                            "required": ["city"]
                        }
                    },
                    "required": ["name"]
                }
            },
            "required": ["company"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(company={
            "name": "Acme",
            "address": {"city": "Beijing", "country": "China"}
        })
        assert instance.company.name == "Acme"
        assert instance.company.address.city == "Beijing"
        assert instance.company.address.country == "China"

    def test_array_of_nested_objects(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "price": {"type": "number"}
                        },
                        "required": ["name", "price"]
                    }
                }
            },
            "required": ["items"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(items=[
            {"name": "apple", "price": 1.5},
            {"name": "banana", "price": 2.0}
        ])
        assert len(instance.items) == 2
        assert instance.items[0].name == "apple"
        assert instance.items[0].price == 1.5
        assert instance.items[1].name == "banana"


class TestRef:

    def test_schema_as_dict(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="test")
        assert instance.name == "test"

    def test_ref_in_array(self):
        schema = '''
        {
            "$defs": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "price": {"type": "number"}
                    },
                    "required": ["name", "price"]
                }
            },
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/Item"}
                }
            },
            "required": ["items"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(items=[
            {"name": "apple", "price": 1.5},
            {"name": "banana", "price": 2.0}
        ])
        assert len(instance.items) == 2
        assert instance.items[0].name == "apple"
        assert instance.items[0].price == 1.5

    def test_multiple_refs(self):
        schema = '''
        {
            "$defs": {
                "Address": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "country": {"type": "string"}
                    },
                    "required": ["city"]
                },
                "Person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "address": {"$ref": "#/$defs/Address"}
                    },
                    "required": ["name"]
                }
            },
            "type": "object",
            "properties": {
                "person": {"$ref": "#/$defs/Person"}
            },
            "required": ["person"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(person={
            "name": "John",
            "address": {"city": "Beijing", "country": "China"}
        })
        assert instance.person.name == "John"
        assert instance.person.address.city == "Beijing"


class TestEnum:

    def test_enum_string_values(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "status": {
                    "enum": ["active", "inactive", "pending"]
                }
            },
            "required": ["status"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(status="active")
        assert instance.status.value == "active"

    def test_enum_mixed_values(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "value": {
                    "enum": [1, 2, 3, "other"]
                }
            },
            "required": ["value"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(value=1)
        assert instance.value.value == 1
        instance2 = model_cls(value="other")
        assert instance2.value.value == "other"


class TestConst:

    def test_const_string(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "type": {
                    "const": "user"
                }
            },
            "required": ["type"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(type="user")
        assert instance.type == "user"

    def test_const_integer(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "version": {
                    "const": 1
                }
            },
            "required": ["version"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(version=1)
        assert instance.version == 1


class TestAnyOfOneOf:

    def test_any_of_string_or_integer(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "value": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "integer"}
                    ]
                }
            },
            "required": ["value"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance1 = model_cls(value="test")
        assert instance1.value == "test"
        instance2 = model_cls(value=123)
        assert instance2.value == 123

    def test_any_of_with_null(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "name": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"}
                    ]
                }
            },
            "required": ["name"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance1 = model_cls(name="test")
        assert instance1.name == "test"
        instance2 = model_cls(name=None)
        assert instance2.name is None

    def test_one_of_types(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "data": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "integer"}
                    ]
                }
            },
            "required": ["data"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(data="test")
        assert instance.data == "test"


class TestAllOf:

    def test_all_of_combines_properties(self):
        schema = '''
        {
            "type": "object",
            "allOf": [
                {
                    "properties": {
                        "name": {"type": "string"}
                    },
                    "required": ["name"]
                },
                {
                    "properties": {
                        "age": {"type": "integer"}
                    },
                    "required": ["age"]
                }
            ]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="John", age=30)
        assert instance.name == "John"
        assert instance.age == 30


class TestMultiType:

    def test_type_array_string_null(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "value": {
                    "type": ["string", "null"]
                }
            },
            "required": ["value"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance1 = model_cls(value="test")
        assert instance1.value == "test"
        instance2 = model_cls(value=None)
        assert instance2.value is None


class TestStringConstraints:

    def test_min_length(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": 3
                }
            },
            "required": ["name"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="John")
        assert instance.name == "John"
        with pytest.raises(ValidationError):
            model_cls(name="Jo")

    def test_max_length(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "maxLength": 5
                }
            },
            "required": ["name"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="John")
        assert instance.name == "John"
        with pytest.raises(ValidationError):
            model_cls(name="John Doe")

    def test_pattern(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "pattern": "^[A-Z]{3}$"
                }
            },
            "required": ["code"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(code="ABC")
        assert instance.code == "ABC"
        with pytest.raises(ValidationError):
            model_cls(code="abc")

    def test_format_email(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email"
                }
            },
            "required": ["email"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(email="test@example.com")
        assert instance.email == "test@example.com"


class TestNumericConstraints:

    def test_minimum(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "age": {
                    "type": "integer",
                    "minimum": 0
                }
            },
            "required": ["age"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(age=25)
        assert instance.age == 25
        with pytest.raises(ValidationError):
            model_cls(age=-1)

    def test_maximum(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "score": {
                    "type": "integer",
                    "maximum": 100
                }
            },
            "required": ["score"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(score=80)
        assert instance.score == 80
        with pytest.raises(ValidationError):
            model_cls(score=101)

    def test_exclusive_minimum(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "value": {
                    "type": "integer",
                    "exclusiveMinimum": 0
                }
            },
            "required": ["value"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(value=1)
        assert instance.value == 1
        with pytest.raises(ValidationError):
            model_cls(value=0)

    def test_exclusive_maximum(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "value": {
                    "type": "integer",
                    "exclusiveMaximum": 10
                }
            },
            "required": ["value"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(value=9)
        assert instance.value == 9
        with pytest.raises(ValidationError):
            model_cls(value=10)

    def test_multiple_of(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "value": {
                    "type": "integer",
                    "multipleOf": 5
                }
            },
            "required": ["value"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(value=15)
        assert instance.value == 15
        with pytest.raises(ValidationError):
            model_cls(value=13)


class TestAdditionalProperties:

    def test_additional_properties_false(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"],
            "additionalProperties": false
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="test")
        assert instance.name == "test"
        with pytest.raises(ValidationError):
            model_cls(name="test", extra="field")


class TestNullType:

    def test_null_type(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "value": {
                    "type": "null"
                }
            },
            "required": ["value"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(value=None)
        assert instance.value is None


class TestErrors:

    def test_invalid_json_string(self):
        with pytest.raises(ValueError, match="Invalid JSON Schema string"):
            json_schema_to_pydantic("not valid json")

    def test_non_object_root_type(self):
        schema = '{"type": "string"}'
        with pytest.raises(ValueError, match="Only object type JSON Schemas are supported"):
            json_schema_to_pydantic(schema)

    def test_model_validation_error(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "age": {"type": "integer"}
            },
            "required": ["age"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        with pytest.raises(ValidationError):
            model_cls(age="not an integer")

    def test_ref_not_found(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "item": {"$ref": "#/$defs/NotFound"}
            }
        }
        '''
        with pytest.raises(ValueError, match="Reference not found"):
            json_schema_to_pydantic(schema)


class TestModelDumpJson:

    def test_model_dump_json(self):
        schema = '''
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"}
            },
            "required": ["name", "count"]
        }
        '''
        model_cls = json_schema_to_pydantic(schema)
        instance = model_cls(name="test", count=5)
        json_str = instance.model_dump_json()
        assert '"name":"test"' in json_str
        assert '"count":5' in json_str
