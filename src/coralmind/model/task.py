from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

__all__ = ["Task", "Material", "OutputFormat", "JsonOutputFormat", "Language"]


class Language(Enum):
    EN = "en"
    CN = "cn"


class Material(BaseModel):
    """
    Material
    """
    name: str = Field(description="Material name")
    content: str = Field(description="Material content")


class JsonOutputFormat(BaseModel):
    """
    JSON output format specification
    """
    format: Literal["json"] = Field(default="json", description="Output format type")
    json_schema: str = Field(description="JSON Schema string for output validation")


OutputFormat = JsonOutputFormat


class Task(BaseModel):
    """
    Input structure
    """
    materials: list[Material] = Field(description="Material-type information")
    requirements: str = Field(description="Reusable output requirements")
    output_format: OutputFormat | None = Field(default=None, description="Output format specification")
    language: Language = Field(default=Language.EN, description="Language for prompts")
