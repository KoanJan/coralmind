from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["Line", "TreeNode", "RequirementNode", "RequirementTree"]


class Line(BaseModel):
    """A line from static splitting of requirements"""
    id: int = Field(description="Line index, starting from 1")
    content: str = Field(description="Line content")


class TreeNode(BaseModel):
    """Simplified tree structure returned by LLM"""
    name: str = Field(description="Node name, concise summary")
    description: str = Field(description="Description of node content")
    children: list[TreeNode] | None = Field(
        default=None,
        description="Child nodes (for non-leaf nodes)"
    )
    scope: list[list[int]] | None = Field(
        default=None,
        description="Scope ranges [[start, end], ...] (for leaf nodes only, mutually exclusive with children)"
    )


class RequirementNode(BaseModel):
    """Full tree node used in code"""
    id: str = Field(description="Unique node identifier")
    name: str = Field(description="Node name")
    fullname: str = Field(description="Full path from root, e.g. 'A-B-C'")
    description: str = Field(description="Description for embedding")
    scope: list[list[int]] | None = Field(
        default=None,
        description="Scope ranges [[start, end], ...] (for leaf nodes only)"
    )
    children: list[RequirementNode] | None = Field(
        default=None,
        description="Child nodes (for non-leaf nodes)"
    )
    embedding: list[float] | None = Field(
        default=None,
        description="Pre-computed embedding vector"
    )


class RequirementTree(BaseModel):
    """Structured requirement tree"""
    lines: list[Line] = Field(description="Original lines from static splitting")
    root: RequirementNode = Field(description="Root node of the tree")

    def get_leaf_nodes(self) -> list[RequirementNode]:
        """Get all leaf nodes (nodes with scope)"""
        leaves: list[RequirementNode] = []

        def collect(node: RequirementNode) -> None:
            if node.scope is not None:
                leaves.append(node)
            elif node.children:
                for child in node.children:
                    collect(child)

        collect(self.root)
        return leaves

    def get_content_by_node(self, node: RequirementNode) -> str:
        """Get original content for a node based on its scope"""
        if node.scope is None:
            return ""

        content_parts: list[str] = []
        line_dict = {line.id: line.content for line in self.lines}

        for start, end in node.scope:
            for line_id in range(start, end + 1):
                if line_id in line_dict:
                    content_parts.append(line_dict[line_id])

        return "\n".join(content_parts)
