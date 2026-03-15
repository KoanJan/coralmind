from importlib import import_module
from typing import Any

from pydantic import BaseModel

from ..model import Language, Task
from .cn import EVALUATION_STANDARD as EVALUATION_STANDARD_CN
from .cn import PLAN_STANDARD as PLAN_STANDARD_CN
from .cn.template import (
    EXECUTOR_REQUIREMENTS as EXECUTOR_REQUIREMENTS_CN,
)
from .cn.template import (
    FIX_MODEL_VALIDATION as FIX_MODEL_VALIDATION_CN,
)
from .cn.template import (
    FORMAT_TO_SCHEMA as FORMAT_TO_SCHEMA_CN,
)
from .cn.template import (
    GLOBAL_REQUIREMENTS_CONTEXT as GLOBAL_REQUIREMENTS_CONTEXT_CN,
)
from .cn.template import (
    OLD_PLAN_ATTACHMENT as OLD_PLAN_ATTACHMENT_CN,
)
from .cn.template import (
    OUTPUT_FORMAT_WITH_NAMES as OUTPUT_FORMAT_WITH_NAMES_CN,
)
from .cn.template import (
    OUTPUT_FORMAT_WITHOUT_NAMES as OUTPUT_FORMAT_WITHOUT_NAMES_CN,
)
from .cn.template import (
    PLANNER_MESSAGE_TEMPLATE as PLANNER_MESSAGE_TEMPLATE_CN,
)
from .cn.template import (
    PLANNER_OUTPUT_FORMAT_SECTION as PLANNER_OUTPUT_FORMAT_SECTION_CN,
)
from .cn.template import (
    RELEVANT_REQUIREMENTS_CONTEXT as RELEVANT_REQUIREMENTS_CONTEXT_CN,
)
from .cn.template import (
    REQUIREMENT_TREE_BUILD as REQUIREMENT_TREE_BUILD_CN,
)
from .en import EVALUATION_STANDARD as EVALUATION_STANDARD_EN
from .en import PLAN_STANDARD as PLAN_STANDARD_EN
from .en.template import (
    EXECUTOR_REQUIREMENTS as EXECUTOR_REQUIREMENTS_EN,
)
from .en.template import (
    FIX_MODEL_VALIDATION as FIX_MODEL_VALIDATION_EN,
)
from .en.template import (
    FORMAT_TO_SCHEMA as FORMAT_TO_SCHEMA_EN,
)
from .en.template import (
    GLOBAL_REQUIREMENTS_CONTEXT as GLOBAL_REQUIREMENTS_CONTEXT_EN,
)
from .en.template import (
    OLD_PLAN_ATTACHMENT as OLD_PLAN_ATTACHMENT_EN,
)
from .en.template import (
    OUTPUT_FORMAT_WITH_NAMES as OUTPUT_FORMAT_WITH_NAMES_EN,
)
from .en.template import (
    OUTPUT_FORMAT_WITHOUT_NAMES as OUTPUT_FORMAT_WITHOUT_NAMES_EN,
)
from .en.template import (
    PLANNER_MESSAGE_TEMPLATE as PLANNER_MESSAGE_TEMPLATE_EN,
)
from .en.template import (
    PLANNER_OUTPUT_FORMAT_SECTION as PLANNER_OUTPUT_FORMAT_SECTION_EN,
)
from .en.template import (
    RELEVANT_REQUIREMENTS_CONTEXT as RELEVANT_REQUIREMENTS_CONTEXT_EN,
)
from .en.template import (
    REQUIREMENT_TREE_BUILD as REQUIREMENT_TREE_BUILD_EN,
)
from .name import PromptName, PromptTemplateName


def _get_module_prefix(language: Language) -> str:
    """Get module prefix for the specified language."""
    if language == Language.EN:
        return "en"
    elif language == Language.CN:
        return "cn"
    else:
        raise ValueError(f"Unsupported language: {language}")


_STATIC_PROMPTS = {
    Language.EN: {
        PromptName.PLAN_STANDARD: PLAN_STANDARD_EN,
        PromptName.EVALUATION_STANDARD: EVALUATION_STANDARD_EN,
    },
    Language.CN: {
        PromptName.PLAN_STANDARD: PLAN_STANDARD_CN,
        PromptName.EVALUATION_STANDARD: EVALUATION_STANDARD_CN,
    },
}


_TEMPLATE_PROMPTS = {
    Language.EN: {
        PromptTemplateName.FIX_MODEL_VALIDATION: FIX_MODEL_VALIDATION_EN,
        PromptTemplateName.OUTPUT_FORMAT_WITH_NAMES: OUTPUT_FORMAT_WITH_NAMES_EN,
        PromptTemplateName.OUTPUT_FORMAT_WITHOUT_NAMES: OUTPUT_FORMAT_WITHOUT_NAMES_EN,
        PromptTemplateName.PLANNER_OUTPUT_FORMAT_SECTION: PLANNER_OUTPUT_FORMAT_SECTION_EN,
        PromptTemplateName.PLANNER_MESSAGE_TEMPLATE: PLANNER_MESSAGE_TEMPLATE_EN,
        PromptTemplateName.OLD_PLAN_ATTACHMENT: OLD_PLAN_ATTACHMENT_EN,
        PromptTemplateName.EXECUTOR_REQUIREMENTS: EXECUTOR_REQUIREMENTS_EN,
        PromptTemplateName.FORMAT_TO_SCHEMA: FORMAT_TO_SCHEMA_EN,
        PromptTemplateName.GLOBAL_REQUIREMENTS_CONTEXT: GLOBAL_REQUIREMENTS_CONTEXT_EN,
        PromptTemplateName.REQUIREMENT_TREE_BUILD: REQUIREMENT_TREE_BUILD_EN,
        PromptTemplateName.RELEVANT_REQUIREMENTS_CONTEXT: RELEVANT_REQUIREMENTS_CONTEXT_EN,
    },
    Language.CN: {
        PromptTemplateName.FIX_MODEL_VALIDATION: FIX_MODEL_VALIDATION_CN,
        PromptTemplateName.OUTPUT_FORMAT_WITH_NAMES: OUTPUT_FORMAT_WITH_NAMES_CN,
        PromptTemplateName.OUTPUT_FORMAT_WITHOUT_NAMES: OUTPUT_FORMAT_WITHOUT_NAMES_CN,
        PromptTemplateName.PLANNER_OUTPUT_FORMAT_SECTION: PLANNER_OUTPUT_FORMAT_SECTION_CN,
        PromptTemplateName.PLANNER_MESSAGE_TEMPLATE: PLANNER_MESSAGE_TEMPLATE_CN,
        PromptTemplateName.OLD_PLAN_ATTACHMENT: OLD_PLAN_ATTACHMENT_CN,
        PromptTemplateName.EXECUTOR_REQUIREMENTS: EXECUTOR_REQUIREMENTS_CN,
        PromptTemplateName.FORMAT_TO_SCHEMA: FORMAT_TO_SCHEMA_CN,
        PromptTemplateName.GLOBAL_REQUIREMENTS_CONTEXT: GLOBAL_REQUIREMENTS_CONTEXT_CN,
        PromptTemplateName.REQUIREMENT_TREE_BUILD: REQUIREMENT_TREE_BUILD_CN,
        PromptTemplateName.RELEVANT_REQUIREMENTS_CONTEXT: RELEVANT_REQUIREMENTS_CONTEXT_CN,
    },
}


def get_prompt(name: PromptName, language: Language | None = None) -> str:
    """
    Get a static prompt by name and language.

    Args:
        name: Prompt name from PromptName enum
        language: Language for the prompt (default: Language.EN)

    Returns:
        Prompt string
    """
    if language is None:
        language = Language.EN
    return _STATIC_PROMPTS[language][name]


def build_prompt(name: PromptTemplateName, language: Language | None = None, **kwargs: Any) -> str:
    """
    Get a prompt template by name and format it with the provided kwargs.

    Args:
        name: Prompt template name from PromptTemplateName enum
        language: Language for the prompt (default: Language.EN)
        **kwargs: Variables to format the prompt template

    Returns:
        Formatted prompt string
    """
    if language is None:
        language = Language.EN
    return _TEMPLATE_PROMPTS[language][name].format(**kwargs)


def build_score_messages(task: Task, output: str) -> list[str]:
    """
    Build messages for scoring task output.

    Args:
        task: Task object containing materials, requirements, and language
        output: Actual output of task execution

    Returns:
        List of message strings for scoring
    """
    if not isinstance(task, Task):
        raise TypeError(f"Expected Task, got {type(task).__name__}")

    module_prefix = _get_module_prefix(task.language)
    func_module = import_module(f".{module_prefix}.func", package=__name__)
    result: list[str] = func_module.build_score_messages(task, output)
    return result


def build_validation_messages(
    language: Language,
    materials: dict[str, str],
    requirements: str,
    output: str | BaseModel,
    output_names: dict[str, str] | None = None,
    output_what: str | None = None,
    relevant_requirements: str | None = None,
) -> list[str]:
    """
    Build messages for validating task output.

    Args:
        language: Language for prompts
        materials: Dictionary of material name to content
        requirements: Task requirements
        output: Actual output (string or BaseModel)
        output_names: Expected output field definitions (for BaseModel output)
        output_what: Expected output description (for str output, defaults to requirements)
        relevant_requirements: Relevant requirements for alignment check (from requirement tree or global fallback)

    Returns:
        List of message strings for validation
    """
    module_prefix = _get_module_prefix(language)
    func_module = import_module(f".{module_prefix}.func", package=__name__)
    result: list[str] = func_module.build_validation_messages(materials, requirements, output, output_names, output_what, relevant_requirements)
    return result


__all__ = [
    "PromptName",
    "PromptTemplateName",
    "get_prompt",
    "build_prompt",
    "build_score_messages",
    "build_validation_messages",
]
