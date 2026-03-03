# Contributing to coralmind

Thank you for considering contributing to coralmind!

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

Please be friendly and respectful. We welcome contributors from all backgrounds.

## How to Contribute

### Reporting Bugs

If you find a bug, please submit it via [GitHub Issues](https://github.com/KoanJan/coralmind/issues). Before submitting:

1. Search existing issues to confirm it's not a duplicate
2. Use a clear title to describe the problem
3. Provide steps to reproduce
4. Describe your environment (Python version, OS, etc.)

### Proposing New Features

New feature suggestions are welcome! Please:

1. Discuss your idea in Issues first
2. Explain the use case for the feature
3. Wait for maintainer feedback before implementing

### Submitting Code

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Write code and tests
4. Ensure all tests pass
5. Submit a Pull Request

## Development Setup

### Clone the Repository

```bash
git clone https://github.com/KoanJan/coralmind.git
cd coralmind
```

### Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows
```

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Run Code Checks

```bash
ruff check src tests
mypy src
```

## Code Style

We use the following tools to maintain code quality:

- **ruff**: Code formatting and linting
- **mypy**: Static type checking

### Type Hints

All public APIs must include type hints:

```python
def process_task(task: Task, options: Optional[dict] = None) -> str:
    ...
```

### Docstrings

Use concise docstrings to describe function behavior:

```python
def score(self, task: Task, output: str) -> int:
    """
    Score the task execution result.
    
    Args:
        task: Task information
        output: Execution output
        
    Returns:
        Integer score from 0-10
    """
```

## Commit Message Guidelines

Use clear, descriptive commit messages:

```
<type>: <description>

[optional body]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation update
- `test`: Test related
- `refactor`: Code refactoring
- `chore`: Miscellaneous (dependency updates, etc.)

**Example**:
```
feat: add async LLM call support

- Support async/await syntax
- Add timeout configuration
- Update related tests
```

## Pull Request Process

1. **Ensure tests pass**: All existing and new tests must pass
2. **Update documentation**: If changing API, update README or related docs
3. **Keep it simple**: One PR should do one thing
4. **Respond to feedback**: Reply to code review comments promptly

### PR Checklist

- [ ] Code passes `ruff check` and `mypy`
- [ ] All tests pass
- [ ] New features have corresponding tests
- [ ] Related documentation updated
- [ ] Commit messages are clear

## Project Structure

```
coralmind/
├── src/coralmind/       # Source code
│   ├── agent.py         # Agent main class
│   ├── worker.py        # Core components
│   ├── model/           # Data models
│   ├── storage/         # Persistence
│   └── strategy/        # Strategy implementations
├── tests/               # Test files
├── docs/                # Documentation
└── examples/            # Example code
```

## Need Help?

If you have any questions, you can:

- Ask in [Issues](https://github.com/KoanJan/coralmind/issues)
- Check the documentation in [README](README.md)

Thank you for your contribution!
