# Promptfoo Evaluation Framework for Orchestrator Routing

This directory contains evaluation tests for the Clarvis orchestrator routing system using [Promptfoo](https://www.promptfoo.dev/).

## Test Summary

| Test Suite | Test Count | Description |
|------------|------------|-------------|
| `routing_eval.yaml` | 30 | Core routing for Gmail, Ski, Notes agents |
| `edge_cases.yaml` | 20 | Edge cases, keyword conflicts, ambiguous queries |
| `follow_up.yaml` | 15 | Multi-turn conversation context |
| **Total** | **65** | |

## Directory Structure

```
evals/
├── README.md              # This file
├── provider.py            # Promptfoo Python provider (loads the router)
├── run_router.py          # CLI harness for manual testing
├── run_router_wrapper.sh  # Shell wrapper (alternative provider)
├── routing_eval.yaml      # Core routing tests
├── edge_cases.yaml        # Edge case tests
└── follow_up.yaml         # Follow-up detection tests
```

## Prerequisites

- Node.js installed (for `npx promptfoo`)
- Python virtual environment activated
- `ANTHROPIC_API_KEY` set in environment (only required for LLM routing tests)

## Quick Start

```bash
# Run all routing evaluations
make eval-all

# Run specific test suites
make eval-routing    # Core routing tests
make eval-edge       # Edge cases and ambiguous queries
make eval-follow     # Follow-up detection tests

# View results in browser
make eval-view
```

## Test Suites

### Core Routing Tests (`routing_eval.yaml`)

Tests the basic routing functionality for each agent:
- **Gmail routing**: Email-related queries
- **Ski routing**: Ski conditions and mountain info
- **Notes routing**: Lists, reminders, and notes
- **Direct handling**: Greetings and thanks

### Edge Case Tests (`edge_cases.yaml`)

Tests ambiguous and edge-case scenarios:
- Queries that could match multiple agents
- Keyword conflicts (e.g., "email me the ski conditions")
- Empty or malformed queries
- Multi-domain queries

### Follow-up Detection Tests (`follow_up.yaml`)

Tests multi-turn conversation context:
- "What about" follow-up phrases
- Short queries with pronouns
- Context continuation

## Test Harness

The `run_router.py` script provides a bridge between promptfoo and the Python router:

```bash
# Basic usage (code-only routing)
echo "check my email" | python evals/run_router.py

# Enable LLM routing for ambiguous queries
echo "help me" | python evals/run_router.py --llm

# Test with conversation context
echo "what about tomorrow?" | python evals/run_router.py --context '{"last_agent": "ski"}'
```

Output format:
```json
{
  "agent_name": "gmail",
  "confidence": 0.8,
  "reasoning": "Code-based routing: matched keywords ['email']",
  "handle_directly": false
}
```

## Adding New Agent Tests

When adding a new agent to the orchestrator:

1. **Add mock agent to `run_router.py`:**
   ```python
   registry.register(MockAgent("newagent", "Description", ["capability1"]))
   ```

2. **Add test cases to `routing_eval.yaml`:**
   ```yaml
   # NewAgent routing
   - vars:
       query: "example query for new agent"
     assert:
       - type: javascript
         value: "JSON.parse(output).agent_name === 'newagent'"
   ```

3. **Add edge cases if keywords overlap with existing agents to `edge_cases.yaml`**

4. **Run evals to verify:**
   ```bash
   make eval-all
   ```

## Understanding Results

Promptfoo evaluates each test case and reports:
- **Pass**: All assertions passed
- **Fail**: One or more assertions failed

Target metrics:
- **Core routing tests**: >95% pass rate
- **Edge cases**: May have lower pass rate for genuinely ambiguous queries
- **Follow-up detection**: >90% pass rate

## Viewing Results

```bash
# Launch the promptfoo web viewer
make eval-view
```

This opens a browser interface showing:
- Pass/fail status for each test
- Detailed assertion results
- Output comparison

## CI Integration

To run evaluations in CI:

```bash
# Run with JSON output for CI parsing
npx promptfoo eval -c evals/routing_eval.yaml --output results.json

# Check exit code (0 = all passed, 1 = some failed)
echo $?
```
