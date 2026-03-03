# API Documentation

This directory contains detailed API documentation.

## Quick Reference

For main APIs, please refer to the "Quick Start" and "Core Concepts" sections in [README.md](../README.md).

## Module Index

### Core Modules

| Module | Description |
|--------|-------------|
| `coralmind.agent` | Agent main class, task execution entry point |
| `coralmind.model` | Data model definitions (Task, Material, Plan, etc.) |
| `coralmind.worker` | Core components (Planner, Executor, Validator, etc.) |
| `coralmind.storage` | Persistent storage |
| `coralmind.strategy` | Strategy implementations (ThresholdStrategy, etc.) |

### Main Classes

#### Agent

```python
from coralmind import Agent, LLMConfig

agent = Agent(
    default_llm=LLMConfig(
        model_id="gpt-4",
        base_url="https://api.openai.com/v1",
        api_key="your-api-key",
    ),
    max_retry_times_per_node=3,
)

result = agent.run(task)
```

#### Task & Material

```python
from coralmind import Task, Material

task = Task(
    materials=[
        Material(name="article", content="..."),
        Material(name="requirements", content="..."),
    ],
    requirements="Generate summary based on the article"
)
```

#### ThresholdStrategy

```python
from coralmind import ThresholdStrategy

strategy = ThresholdStrategy(
    s0=8.0,   # BASE_ON threshold
    s1=9.0,   # USE threshold
    c=3,      # Minimum historical records
)
```

## Detailed Documentation

Complete API documentation is under construction. For now, please refer to:

- [README.md](../README.md) - Quick start and core concepts
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guide
- [Source code](../src/coralmind/) - Implementation code with detailed comments
