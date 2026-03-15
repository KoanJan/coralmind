from enum import Enum


class PromptName(Enum):
    PLAN_STANDARD = "plan_standard"
    EVALUATION_STANDARD = "evaluation_standard"


class PromptTemplateName(Enum):
    FIX_DICT_STRUCTURE = "fix_dict_structure"
    FIX_MODEL_VALIDATION = "fix_model_validation"
    OUTPUT_FORMAT_WITH_NAMES = "output_format_with_names"
    OUTPUT_FORMAT_WITHOUT_NAMES = "output_format_without_names"
    PLANNER_OUTPUT_FORMAT_SECTION = "planner_output_format_section"
    PLANNER_MESSAGE_TEMPLATE = "planner_message_template"
    OLD_PLAN_ATTACHMENT = "old_plan_attachment"
    EXECUTOR_REQUIREMENTS = "executor_requirements"
    FORMAT_TO_SCHEMA = "format_to_schema"
    GLOBAL_REQUIREMENTS_CONTEXT = "global_requirements_context"
    REQUIREMENT_TREE_BUILD = "requirement_tree_build"
    RELEVANT_REQUIREMENTS_CONTEXT = "relevant_requirements_context"
