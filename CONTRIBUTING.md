# Contributing to Clarvis

Thank you for your interest in contributing to Clarvis! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.12+ (not 3.14 - some dependencies lack wheel support)
- Node.js 18+ (for npx/MCP servers)
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/jhcahoon/clarvis.git
cd clarvis

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate     # Linux/Mac
.venv\Scripts\activate        # Windows

# Copy and configure local settings
cp configs/mcp_servers.json.example configs/mcp_servers.local.json
cp .env.example .env
# Edit .env with your API keys
```

## Code Style

We use the following tools to maintain code quality:

### Linting and Formatting

```bash
# Check for linting issues
ruff check clarvis_agents/

# Auto-fix linting issues
ruff check --fix clarvis_agents/

# Format code
black clarvis_agents/

# Type checking
mypy clarvis_agents/
```

### Style Guidelines

- Follow PEP 8 conventions
- Use type hints for all function arguments and return values
- Add `-> None` return type to `__init__` methods
- Keep lines under 100 characters
- Use docstrings for public functions and classes
- Avoid unnecessary comments - code should be self-documenting

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_gmail_agent.py -v

# Run tests with coverage
pytest tests/ -v --cov=clarvis_agents --cov-report=html

# Run integration tests (requires running API server)
pytest tests/ -v -m integration
```

### Writing Tests

- Place tests in the `tests/` directory
- Follow the existing test structure (unit tests in `test_core/`, `test_orchestrator/`, etc.)
- Use pytest fixtures for common setup
- Mock external services in unit tests
- Mark integration tests with `@pytest.mark.integration`

## Pull Request Process

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the code style guidelines
3. **Add tests** for any new functionality
4. **Run the test suite** to ensure all tests pass
5. **Update documentation** if needed (README, architecture docs, docstrings)
6. **Create a pull request** with a clear description of changes

### PR Guidelines

- Keep PRs focused on a single feature or fix
- Write clear commit messages
- Reference any related issues
- Ensure CI checks pass before requesting review

## Adding New Agents

When adding a new agent:

1. Create a new directory under `clarvis_agents/` following the existing pattern
2. Implement the `BaseAgent` interface from `clarvis_agents/core/`
3. Register the agent with the orchestrator
4. Add routing patterns to `clarvis_agents/orchestrator/classifier.py`
5. Update routing announcements in `clarvis_agents/orchestrator/agent.py`
6. Add tests for the new agent
7. Update architecture documentation

See `docs/agent_architecture.md` for detailed guidance.

## Evaluation Tests

We use Promptfoo for routing evaluation tests:

```bash
# Run all evaluations
make eval-all

# Run specific test suites
make eval-routing    # Core routing tests
make eval-edge       # Edge case tests
make eval-follow     # Follow-up detection tests

# View results
make eval-view
```

When adding new agents, add corresponding tests to `evals/routing_eval.yaml`.

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include steps to reproduce for bugs
- Check existing issues before creating a new one

## Security

If you discover a security vulnerability, please see [SECURITY.md](SECURITY.md) for reporting instructions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
