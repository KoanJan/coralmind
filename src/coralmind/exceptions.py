"""
CoralMind Custom Exceptions

This module defines custom exception classes for better error handling and debugging.
All exceptions inherit from CoralMindError for easy catching.
"""


class CoralMindError(Exception):
    """Base exception for all CoralMind errors"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class PlanValidationError(CoralMindError):
    """Raised when plan validation fails"""

    def __init__(self, message: str, node_id: str | None = None):
        self.node_id = node_id
        if node_id:
            message = f"[Node: {node_id}] {message}"
        super().__init__(message)


class ExecutionError(CoralMindError):
    """Raised when task execution fails"""

    def __init__(self, message: str, node_id: str | None = None):
        self.node_id = node_id
        if node_id:
            message = f"[Node: {node_id}] {message}"
        super().__init__(message)


class StorageError(CoralMindError):
    """Raised when storage operations fail"""

    def __init__(self, message: str, operation: str | None = None):
        self.operation = operation
        if operation:
            message = f"[{operation}] {message}"
        super().__init__(message)


class ConfigurationError(CoralMindError):
    """Raised when configuration is invalid"""

    def __init__(self, message: str, parameter: str | None = None):
        self.parameter = parameter
        if parameter:
            message = f"[Parameter: {parameter}] {message}"
        super().__init__(message)


class LLMError(CoralMindError):
    """Raised when LLM operations fail"""

    def __init__(self, message: str, model: str | None = None):
        self.model = model
        if model:
            message = f"[Model: {model}] {message}"
        super().__init__(message)
