from enum import Enum, IntEnum
from typing import Any

from pydantic import BaseModel, Field, create_model

from .task import Language

__all__ = ["InputFieldSourceType", "InputField", "OutputType", "OutputConstraints", "PlanNode", "Plan", "PlanAdvice", "PlanAdviceType", "TaskStep"]


class InputFieldSourceType(str, Enum):
    """
    Input field source type
    """
    ORIGINAL_MATERIAL = "original_material"
    OUTPUT_OF_ANOTHER_NODE = "output_of_another_node"


class InputField(BaseModel):
    """
    Input field description
    """
    source_type: InputFieldSourceType = Field(description="Input field source type")
    material_name: str = Field(description="Material name (only when source_type=original_material)")

    class OutputOfAnotherNode(BaseModel):
        node_id: str
        output_field_name: str

    output_of_another_node: OutputOfAnotherNode | None = Field(
        default=None, description="Which node's output to use (only when source_type=output_of_another_node)"
    )


class OutputType(str, Enum):
    """
    Output type
    """
    TEXT = "text"
    MODEL = "model"


class OutputConstraints(BaseModel):
    """
    Output constraints for validation

    Validation has two levels:
    - Format validation: output_type + fields (for MODEL type, dynamically create BaseModel for validation)
    - Semantic validation: content_spec (for both types, validate content matches expectation)
    """
    output_type: OutputType = Field(description="Output format type: text or model")
    fields: dict[str, str] | None = Field(
        default=None,
        description="Field definitions for MODEL type (field_name -> field_description), used for format validation"
    )
    content_spec: str = Field(
        description="Content specification for semantic validation (expected output content description)"
    )

    def get_model_class(self, model_name: str = "DynamicOutput") -> type[BaseModel] | None:
        """
        Get the dynamically created BaseModel class for MODEL type output

        Args:
            model_name: Name for the dynamically created model

        Returns:
            A dynamically created BaseModel class, or None if output_type is TEXT or fields is None
        """
        if self.output_type != OutputType.MODEL or self.fields is None:
            return None

        field_definitions: dict[str, tuple[type[str], Any]] = {}
        for field_name, field_description in self.fields.items():
            field_definitions[field_name] = (str, Field(description=field_description))

        return create_model(model_name, __base__=BaseModel, **field_definitions)  # type: ignore[call-overload,no-any-return]


class PlanNode(BaseModel):
    """Plan node description"""
    id: str = Field(description="Node ID, unique within plan")
    input_fields: list[InputField] = Field(description="Describe what inputs the node needs")
    requirements: str = Field(description="Describe the task this node undertakes")
    output_constraints: OutputConstraints = Field(
        description="Output constraints for validation (format and semantic validation)"
    )
    is_final_node: bool = Field(description="Whether this is the final node")


class Plan(BaseModel):
    """Execution plan"""
    deliverable: str = Field(description="Description of the final deliverable")
    nodes: list[PlanNode]


class PlanAdviceType(IntEnum):
    """Advice type"""
    BASE_ON = 1
    USE = 2


class PlanAdvice(BaseModel):
    """Plan advice"""
    type: PlanAdviceType = Field(description="Advice type")
    old_plan: Plan = Field(description="Old plan")


class TaskStep(BaseModel):
    """Task step for execution"""
    materials: dict[str, str] = Field(description="Input material dictionary, key is material name, value is material content")
    requirements: str = Field(description="Task requirement description")
    output_constraints: OutputConstraints = Field(description="Output constraints for validation")
    language: Language | None = Field(default=None, description="Language for prompts")
    relevant_requirements: str | None = Field(default=None, description="Relevant requirements for context")
