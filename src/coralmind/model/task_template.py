from pydantic import BaseModel, Field

__all__ = ["TaskTemplate"]


class TaskTemplate(BaseModel):
    """
    Task template
    """
    material_names: list[str] = Field(description="Material name list")
    requirements: str = Field(description="Reusable output requirements")
