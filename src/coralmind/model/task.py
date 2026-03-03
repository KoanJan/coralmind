from pydantic import BaseModel, Field

__all__ = ["Task", "Material"]


class Material(BaseModel):
    """
    Material
    """
    name: str = Field(description="Material name")
    content: str = Field(description="Material content")


class Task(BaseModel):
    """
    Input structure
    """
    materials: list[Material] = Field(description="Material-type information")
    requirements: str = Field(description="Reusable output requirements")
