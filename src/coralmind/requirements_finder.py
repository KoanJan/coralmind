from __future__ import annotations

import logging
from typing import cast

import numpy as np

from .llm import LLMConfig, as_user_messages, call_llm, get_embedding
from .model import Language
from .model.requirement_tree import Line, RequirementNode, RequirementTree, TreeNode
from .prompts import PromptTemplateName, build_prompt

logger = logging.getLogger(__name__)

__all__ = ["RelevantRequirementsFinder"]

REQUIREMENT_TREE_THRESHOLD = 1000
MISSING_RATIO_WARNING_THRESHOLD = 0.05


def _is_small_requirements(requirements: str) -> bool:
    """Check if requirements is small enough to skip tree building"""
    return len(requirements) < REQUIREMENT_TREE_THRESHOLD


class _RequirementTreeBuilder:
    """Builder for creating structured requirement trees"""

    def __init__(self, llm: LLMConfig, embedding_llm: LLMConfig):
        self.llm = llm
        self.embedding_llm = embedding_llm

    def build(self, requirements: str, language: Language | None = None) -> RequirementTree:
        """
        Build a structured requirement tree from requirements text.

        Args:
            requirements: The requirements text to structure
            language: Language for prompts (default: Language.EN)

        Returns:
            RequirementTree with lines and root node
        """
        if language is None:
            language = Language.EN

        logger.debug(f"Building requirement tree for text (length={len(requirements)})")

        lines = self._split_requirements(requirements)
        logger.debug(f"Split into {len(lines)} lines")

        tree_node = self._build_tree_with_llm(lines, language)
        logger.debug(f"LLM built tree with root: {tree_node.name}")

        self._validate_tree_coverage(tree_node, lines)
        logger.debug("Tree coverage validated: all segments are covered")

        root = self._convert_to_requirement_node(tree_node, "")
        logger.debug(f"Converted to RequirementNode tree with {self._count_leaf_nodes(root)} leaf nodes")

        self._compute_embeddings(root)
        logger.debug("Computed embeddings for all leaf nodes")

        return RequirementTree(lines=lines, root=root)

    def _split_requirements(self, requirements: str) -> list[Line]:
        """Split requirements into lines by newline"""
        lines: list[Line] = []
        line_id = 1

        for line in requirements.split('\n'):
            line = line.strip()
            if line:
                lines.append(Line(id=line_id, content=line))
                line_id += 1

        return lines

    def _build_tree_with_llm(self, lines: list[Line], language: Language) -> TreeNode:
        """Use LLM to build a tree structure from lines"""
        lines_text = "\n".join([f"[{line.id}] {line.content}" for line in lines])

        prompt = build_prompt(
            PromptTemplateName.REQUIREMENT_TREE_BUILD,
            language=language,
            lines_text=lines_text
        )

        response = call_llm(self.llm, as_user_messages([prompt]), TreeNode, self.llm)
        return cast(TreeNode, response.content)

    def _convert_to_requirement_node(
        self,
        tree_node: TreeNode,
        parent_fullname: str
    ) -> RequirementNode:
        """Convert TreeNode to RequirementNode with fullname"""
        fullname = tree_node.name if not parent_fullname else f"{parent_fullname}-{tree_node.name}"
        node_id = fullname.lower().replace(" ", "_").replace("-", "_")

        if tree_node.scope is not None:
            return RequirementNode(
                id=node_id,
                name=tree_node.name,
                fullname=fullname,
                description=tree_node.description,
                scope=tree_node.scope,
                children=None,
                embedding=None
            )

        children: list[RequirementNode] | None = None
        if tree_node.children:
            children = [
                self._convert_to_requirement_node(child, fullname)
                for child in tree_node.children
            ]

        return RequirementNode(
            id=node_id,
            name=tree_node.name,
            fullname=fullname,
            description=tree_node.description,
            scope=None,
            children=children,
            embedding=None
        )

    def _compute_embeddings(self, node: RequirementNode) -> None:
        """Compute embeddings for all leaf nodes"""
        if node.scope is not None:
            embedding = get_embedding(self.embedding_llm, node.description)
            node.embedding = embedding
            logger.debug(f"Computed embedding for leaf node: {node.fullname}")
        elif node.children:
            for child in node.children:
                self._compute_embeddings(child)

    def _count_leaf_nodes(self, node: RequirementNode) -> int:
        """Count leaf nodes in the tree"""
        if node.scope is not None:
            return 1
        if node.children:
            return sum(self._count_leaf_nodes(child) for child in node.children)
        return 0

    def _validate_tree_coverage(self, tree_node: TreeNode, lines: list[Line]) -> None:
        """
        Validate that all line IDs are covered by leaf nodes' scopes.
        If some IDs are missing, automatically add them to an "Other" fallback node.
        """
        total_lines = len(lines)
        if total_lines == 0:
            return

        covered_ids: set[int] = set()

        def collect_scopes(node: TreeNode) -> None:
            if node.scope is not None:
                for start, end in node.scope:
                    for line_id in range(start, end + 1):
                        covered_ids.add(line_id)
            elif node.children:
                for child in node.children:
                    collect_scopes(child)

        collect_scopes(tree_node)

        expected_ids = set(range(1, total_lines + 1))
        missing_ids = expected_ids - covered_ids

        if missing_ids:
            missing_ratio = len(missing_ids) / total_lines
            if missing_ratio >= MISSING_RATIO_WARNING_THRESHOLD:
                logger.warning(
                    f"Tree coverage incomplete: missing {len(missing_ids)}/{total_lines} "
                    f"({missing_ratio:.1%}) line IDs: {sorted(missing_ids)}. "
                    f"Auto-fixing by adding fallback node."
                )
            self._add_fallback_node(tree_node, missing_ids)

    def _add_fallback_node(self, tree_node: TreeNode, missing_ids: set[int]) -> None:
        """
        Add a fallback node to cover missing line IDs.

        Args:
            tree_node: The root node of the tree
            missing_ids: Set of line IDs that are not covered
        """
        sorted_ids = sorted(missing_ids)
        scopes: list[list[int]] = []
        start = sorted_ids[0]
        end = sorted_ids[0]

        for i in range(1, len(sorted_ids)):
            if sorted_ids[i] == end + 1:
                end = sorted_ids[i]
            else:
                scopes.append([start, end])
                start = sorted_ids[i]
                end = sorted_ids[i]
        scopes.append([start, end])

        fallback_node = TreeNode(
            name="Other",
            description="Other requirements not categorized",
            scope=scopes,
            children=None
        )

        if tree_node.children is None:
            tree_node.children = []
        tree_node.children.append(fallback_node)
        logger.info(f"Added fallback node 'Other' with scopes: {scopes}")


def _find_relevant_nodes(
    tree: RequirementTree,
    query: str,
    embedding_llm: LLMConfig,
    top_k: int = 3
) -> list[RequirementNode]:
    """
    Find the most relevant leaf nodes for a query using cosine similarity.

    Args:
        tree: The requirement tree to search
        query: The query text (e.g., plan_node.requirements)
        embedding_llm: LLM config for embedding
        top_k: Number of top results to return

    Returns:
        List of top-k most relevant RequirementNode objects
    """
    leaf_nodes = tree.get_leaf_nodes()
    if not leaf_nodes:
        return []

    if not leaf_nodes[0].embedding:
        query_embedding = get_embedding(embedding_llm, query)
        for node in leaf_nodes:
            if node.embedding is None:
                node.embedding = get_embedding(embedding_llm, node.description)

    query_embedding = get_embedding(embedding_llm, query)

    similarities: list[tuple[float, RequirementNode]] = []
    for node in leaf_nodes:
        if node.embedding:
            sim = _cosine_similarity(query_embedding, node.embedding)
            similarities.append((sim, node))

    similarities.sort(key=lambda x: x[0], reverse=True)

    return [node for _, node in similarities[:top_k]]


class RelevantRequirementsFinder:
    """
    Finder for relevant requirements.

    Automatically handles two modes:
    - Tree mode: When requirements is large, builds/uses requirement tree for semantic search
    - Fallback mode: When requirements is small, returns full requirements directly

    The caller doesn't need to know which mode is being used.
    """

    def __init__(
        self,
        llm: LLMConfig,
        embedding_llm: LLMConfig | None,
        requirements: str,
        task_template_id: int,
        language: Language | None = None
    ):
        self._llm = llm
        self._embedding_llm = embedding_llm
        self._requirements = requirements
        self._task_template_id = task_template_id
        self._language = language or Language.EN
        self._tree: RequirementTree | None = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazily initialize the tree if needed."""
        if self._initialized:
            return

        self._initialized = True

        if _is_small_requirements(self._requirements):
            return

        if self._embedding_llm is None:
            logger.warning("embedding_llm is not configured, falling back to full requirements mode")
            return

        from .storage import RequirementTreeStorage

        ro = RequirementTreeStorage.get_by_task_template_id(self._task_template_id)
        if ro:
            self._tree = ro.to_tree()
            return

        builder = _RequirementTreeBuilder(self._llm, self._embedding_llm)
        self._tree = builder.build(self._requirements, self._language)

        RequirementTreeStorage.upsert(self._task_template_id, self._tree)

    def find(self, node_requirements: str, top_k: int = 3) -> str | None:
        """
        Find relevant requirements for a node.

        Args:
            node_requirements: The requirements of the current node (used for similarity matching)
            top_k: Number of top results to return in tree mode

        Returns:
            Relevant requirements string, or None if no relevant content found in tree mode
        """
        self._ensure_initialized()

        if self._tree is None:
            return self._requirements

        assert self._embedding_llm is not None
        relevant_nodes = _find_relevant_nodes(self._tree, node_requirements, self._embedding_llm, top_k=top_k)

        if not relevant_nodes:
            other_node = self._find_other_node()
            if other_node:
                content = self._tree.get_content_by_node(other_node)
                if content:
                    return f"## {other_node.fullname}\n{content}"
            return None

        content_parts: list[str] = []
        for node in relevant_nodes:
            content = self._tree.get_content_by_node(node)
            if content:
                content_parts.append(f"## {node.fullname}\n{content}")

        return "\n\n".join(content_parts) if content_parts else None

    def _find_other_node(self) -> RequirementNode | None:
        """Find the 'Other' fallback node in the tree."""
        leaf_nodes = self._tree.get_leaf_nodes() if self._tree else []
        for node in leaf_nodes:
            if node.name == "Other":
                return node
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors using numpy"""
    vec_a = np.array(a)
    vec_b = np.array(b)

    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))
