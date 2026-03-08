# Examples

This directory contains usage examples for coralmind.

## Example List

| File | Level | Description |
|------|-------|-------------|
| [01_basic_summary.py](01_basic_summary.py) | Basic | Single material text summarization task |
| [02_multi_material_analysis.py](02_multi_material_analysis.py) | Intermediate | Multi-material comprehensive analysis task |
| [03_custom_strategy.py](03_custom_strategy.py) | Advanced | Custom strategy parameter configuration |
| [04_code_review.py](04_code_review.py) | Advanced | Multi-file code review with env-based LLM config |
| [05_planner_prompt_test.py](05_planner_prompt_test.py) | Test | Validate Planner prompt fix for output_format handling |

## Running Examples

### 1. Set Environment Variables

```bash
export OPENAI_API_KEY="your-api-key"
```

### 2. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 3. Run Example

```bash
cd examples
python 01_basic_summary.py
```

## Example Descriptions

### 01_basic_summary.py

The simplest usage: single material input, execute summarization task.

**Core Concepts**:
- `Material`: Input data unit
- `Task`: Task definition
- `Agent.run()`: Execute task

### 02_multi_material_analysis.py

Demonstrates multi-material input scenario: market report + competitor analysis + user survey → product strategy.

**Core Concepts**:
- Semantic naming of multiple `Material` objects
- Agent automatically plans multi-node execution flow

### 03_custom_strategy.py

Demonstrates how to customize strategy parameters:

```python
strategy = ThresholdStrategy(
    s0=7.0,   # BASE_ON threshold
    s1=8.5,   # USE threshold
    c=2,      # Minimum historical records
)
```

**Core Concepts**:
- `ThresholdStrategy`: Plan selection strategy
- Adjust thresholds to control reuse behavior

### 04_code_review.py

Complex task with environment-based LLM configuration. Ideal for testing and deployment.

**Environment Variables**:
```bash
# Default LLM (required)
export DEFAULT_MODEL_ID="gpt-4o-mini"
export DEFAULT_BASE_URL="https://api.openai.com/v1"
export DEFAULT_API_KEY="sk-xxx"
export DEFAULT_MAX_TOKENS="8196"  # optional

# Planner LLM (optional, uses default if not set)
export PLANNER_MODEL_ID="gpt-4o"
export PLANNER_BASE_URL="https://api.openai.com/v1"
export PLANNER_API_KEY="sk-xxx"
```

**Core Concepts**:
- Environment-based configuration for flexible deployment
- Multi-material code analysis task
- Separation of planner and executor LLMs

## Advanced Usage

### Layered LLM Configuration

```python
agent = Agent(
    default_llm=default_llm,
    planner_llm=planning_llm,      # Use stronger model for planning
    executor_llm=execution_llm,    # Use faster model for execution
)
```

### Custom Database Path

```python
import coralmind

coralmind.set_db_path("/path/to/your/coralmind.db")
```

### Logging Configuration

```python
import logging

logging.getLogger('coralmind').setLevel(logging.DEBUG)
```
