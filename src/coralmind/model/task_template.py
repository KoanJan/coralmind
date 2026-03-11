from __future__ import annotations

from pydantic import BaseModel, Field

from .task import Language, OutputFormat

__all__ = ["TaskTemplate"]


class TaskTemplate(BaseModel):
    """
    Task template
    """
    material_names: list[str] = Field(description="Material name list")
    requirements: str = Field(description="Reusable output requirements")
    output_format: OutputFormat | None = Field(default=None, description="Output format specification")
    language: Language = Field(default=Language.EN, description="Language for prompts")
