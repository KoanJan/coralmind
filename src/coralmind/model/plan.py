from enum import Enum, IntEnum

from pydantic import BaseModel, Field

__all__ = ["InputFieldSourceType", "InputField", "PlanNode", "Plan", "PlanAdvice", "PlanAdviceType"]


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


class PlanNode(BaseModel):
    """Plan node description"""
    id: str = Field(description="Node ID, unique within plan")
    input_fields: list[InputField] = Field(description="Describe what inputs the node needs")
    requirements: str = Field(description="Describe the task this node undertakes")
    output_names: dict[str, str] | None = Field(
        default=None,
        description="Describe what fields the node outputs and their definitions (null when is_final_node=True, example: {'a': 'description of a'})"
    )
    is_final_node: bool = Field(description="Whether this is the final node")


class Plan(BaseModel):
    """Execution plan"""
    nodes: list[PlanNode]


class PlanAdviceType(IntEnum):
    """Advice type"""
    BASE_ON = 1
    USE = 2


class PlanAdvice(BaseModel):
    """Plan advice"""
    type: PlanAdviceType = Field(description="Advice type")
    old_plan: Plan = Field(description="Old plan")
