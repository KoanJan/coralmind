from unittest.mock import MagicMock, patch

from coralmind import LLMConfig
from coralmind.model.requirement_tree import Line, RequirementNode, RequirementTree
from coralmind.requirements_finder import RelevantRequirementsFinder, _is_small_requirements

FakeLLMConfig = LLMConfig(
    model_id="fake-model",
    base_url="https://fake.api/v1",
    api_key="fake-api-key",
)


class TestIsSmallRequirements:
    def test_small_requirements(self):
        assert _is_small_requirements("short text") is True

    def test_large_requirements(self):
        large_text = "x" * 1500
        assert _is_small_requirements(large_text) is False

    def test_boundary_case(self):
        boundary_text = "x" * 999
        assert _is_small_requirements(boundary_text) is True

        boundary_text = "x" * 1000
        assert _is_small_requirements(boundary_text) is False


class TestRelevantRequirementsFinderFallbackMode:
    def test_small_requirements_returns_full_text(self):
        small_requirements = "This is a small requirement text."
        finder = RelevantRequirementsFinder(FakeLLMConfig, FakeLLMConfig, small_requirements, task_template_id=1)

        result = finder.find("some query")
        assert result == small_requirements

    def test_small_requirements_no_tree_building(self):
        small_requirements = "Small text"
        finder = RelevantRequirementsFinder(FakeLLMConfig, FakeLLMConfig, small_requirements, task_template_id=2)

        with patch('coralmind.requirements_finder._RequirementTreeBuilder') as mock_builder:
            finder.find("query")
            mock_builder.assert_not_called()

    def test_none_embedding_llm_falls_back_to_full_requirements(self):
        large_requirements = "x" * 1500
        finder = RelevantRequirementsFinder(FakeLLMConfig, None, large_requirements, task_template_id=3)

        result = finder.find("some query")
        assert result == large_requirements


class TestRelevantRequirementsFinderTreeMode:
    def _create_mock_tree(self) -> RequirementTree:
        lines = [
            Line(id=1, content="First requirement about authentication."),
            Line(id=2, content="Second requirement about database."),
            Line(id=3, content="Third requirement about API design."),
            Line(id=4, content="Fourth requirement about logging."),
            Line(id=5, content="Fifth requirement about caching."),
        ]

        root = RequirementNode(
            id="root",
            name="Requirements",
            fullname="Requirements",
            description="All requirements",
            scope=None,
            children=[
                RequirementNode(
                    id="auth",
                    name="Authentication",
                    fullname="Requirements-Authentication",
                    description="Authentication related requirements",
                    scope=[[1, 1]],
                    children=None,
                    embedding=[0.1, 0.2, 0.3],
                ),
                RequirementNode(
                    id="database",
                    name="Database",
                    fullname="Requirements-Database",
                    description="Database related requirements",
                    scope=[[2, 2]],
                    children=None,
                    embedding=[0.4, 0.5, 0.6],
                ),
                RequirementNode(
                    id="api",
                    name="API",
                    fullname="Requirements-API",
                    description="API design requirements",
                    scope=[[3, 3]],
                    children=None,
                    embedding=[0.7, 0.8, 0.9],
                ),
            ],
        )

        return RequirementTree(lines=lines, root=root)

    def test_tree_mode_returns_relevant_content(self):
        large_requirements = "x" * 1500
        finder = RelevantRequirementsFinder(FakeLLMConfig, FakeLLMConfig, large_requirements, task_template_id=10)

        mock_tree = self._create_mock_tree()
        finder._tree = mock_tree
        finder._initialized = True

        with patch('coralmind.requirements_finder.get_embedding') as mock_embedding:
            mock_embedding.return_value = [0.1, 0.2, 0.3]

            result = finder.find("authentication requirements")

            assert result is not None
            assert "Authentication" in result

    def test_tree_mode_returns_none_when_no_match(self):
        large_requirements = "x" * 1500
        finder = RelevantRequirementsFinder(FakeLLMConfig, FakeLLMConfig, large_requirements, task_template_id=11)

        lines = [Line(id=1, content="Some content")]
        root = RequirementNode(
            id="root",
            name="Root",
            fullname="Root",
            description="Root node",
            scope=None,
            children=[],
        )
        mock_tree = RequirementTree(lines=lines, root=root)
        finder._tree = mock_tree
        finder._initialized = True

        result = finder.find("any query")
        assert result is None

    def test_tree_mode_with_empty_leaf_nodes(self):
        large_requirements = "x" * 1500
        finder = RelevantRequirementsFinder(FakeLLMConfig, FakeLLMConfig, large_requirements, task_template_id=12)

        lines = [Line(id=1, content="Some content")]
        root = RequirementNode(
            id="root",
            name="Root",
            fullname="Root",
            description="Root node",
            scope=None,
            children=[],
        )
        mock_tree = RequirementTree(lines=lines, root=root)
        finder._tree = mock_tree
        finder._initialized = True

        result = finder.find("any query")
        assert result is None


class TestRelevantRequirementsFinderLazyInitialization:
    def test_lazy_initialization(self):
        large_requirements = "x" * 1500
        finder = RelevantRequirementsFinder(FakeLLMConfig, FakeLLMConfig, large_requirements, task_template_id=20)

        assert finder._initialized is False
        assert finder._tree is None

        mock_tree = RequirementTree(
            lines=[Line(id=1, content="test")],
            root=RequirementNode(
                id="root",
                name="Root",
                fullname="Root",
                description="Root",
                scope=[[1, 1]],
                embedding=[0.1],
            ),
        )

        with patch('coralmind.storage.RequirementTreeStorage') as mock_storage:
            mock_storage.get_by_task_template_id.return_value = None

            with patch('coralmind.requirements_finder._RequirementTreeBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.build.return_value = mock_tree
                mock_builder_class.return_value = mock_builder

                with patch('coralmind.requirements_finder.get_embedding') as mock_embedding:
                    mock_embedding.return_value = [0.1]
                    finder.find("query")

                assert finder._initialized is True
                mock_builder_class.assert_called_once_with(FakeLLMConfig, FakeLLMConfig)
                mock_builder.build.assert_called_once()

    def test_no_reinitialization(self):
        large_requirements = "x" * 1500
        finder = RelevantRequirementsFinder(FakeLLMConfig, FakeLLMConfig, large_requirements, task_template_id=21)
        finder._initialized = True
        finder._tree = RequirementTree(
            lines=[Line(id=1, content="test")],
            root=RequirementNode(
                id="root",
                name="Root",
                fullname="Root",
                description="Root",
                scope=[[1, 1]],
                embedding=[0.1],
            ),
        )

        with patch('coralmind.requirements_finder._RequirementTreeBuilder') as mock_builder:
            with patch('coralmind.requirements_finder.get_embedding') as mock_embedding:
                mock_embedding.return_value = [0.1]
                finder.find("query")
                finder.find("another query")
            mock_builder.assert_not_called()


class TestRelevantRequirementsFinderWithTaskTemplateId:
    def test_loads_existing_tree_from_storage(self):
        large_requirements = "x" * 1500
        finder = RelevantRequirementsFinder(
            FakeLLMConfig,
            FakeLLMConfig,
            large_requirements,
            task_template_id=123
        )

        mock_tree = RequirementTree(
            lines=[Line(id=1, content="stored content")],
            root=RequirementNode(
                id="root",
                name="Root",
                fullname="Root",
                description="Root",
                scope=[[1, 1]],
                embedding=[0.5],
            ),
        )

        mock_ro = MagicMock()
        mock_ro.to_tree.return_value = mock_tree

        with patch('coralmind.storage.RequirementTreeStorage') as mock_storage:
            mock_storage.get_by_task_template_id.return_value = mock_ro

            with patch('coralmind.requirements_finder.get_embedding') as mock_embedding:
                mock_embedding.return_value = [0.5]
                result = finder.find("query")

            mock_storage.get_by_task_template_id.assert_called_once_with(123)
            assert result is not None

    def test_builds_and_saves_new_tree(self):
        large_requirements = "x" * 1500
        finder = RelevantRequirementsFinder(
            FakeLLMConfig,
            FakeLLMConfig,
            large_requirements,
            task_template_id=456
        )

        mock_tree = RequirementTree(
            lines=[Line(id=1, content="new content")],
            root=RequirementNode(
                id="root",
                name="Root",
                fullname="Root",
                description="Root",
                scope=[[1, 1]],
                embedding=[0.3],
            ),
        )

        with patch('coralmind.storage.RequirementTreeStorage') as mock_storage:
            mock_storage.get_by_task_template_id.return_value = None

            with patch('coralmind.requirements_finder._RequirementTreeBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.build.return_value = mock_tree
                mock_builder_class.return_value = mock_builder

                with patch('coralmind.requirements_finder.get_embedding') as mock_embedding:
                    mock_embedding.return_value = [0.3]
                    finder.find("query")

                mock_storage.upsert.assert_called_once_with(456, mock_tree)
