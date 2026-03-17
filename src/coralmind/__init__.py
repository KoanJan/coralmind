__version__ = "0.0.11"

import logging

from .agent import Agent
from .exceptions import (
    ConfigurationError,
    CoralMindError,
    ExecutionError,
    LLMError,
    PlanValidationError,
    StorageError,
)
from .llm import LLMConfig, LLMResponse, TokenCost
from .model import Language, Material, OutputFormat, Task
from .storage.connection import set_db_path
from .strategy.advising import BasePlanStrategy, PlanAdviceAction, PlanRecord, PlanStrategyResult, ThresholdStrategy

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "Agent", "Task", "Material", "OutputFormat", "Language", "LLMConfig", "LLMResponse", "TokenCost", "set_db_path",
    "BasePlanStrategy", "ThresholdStrategy", "PlanRecord", "PlanStrategyResult", "PlanAdviceAction",
    "CoralMindError", "PlanValidationError", "ExecutionError", "StorageError", "ConfigurationError", "LLMError",
    "__version__",
]
