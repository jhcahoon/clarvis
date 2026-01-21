#!/bin/bash
# Wrapper script for promptfoo exec provider
# Passes the first argument (the query) to run_router.py via stdin

# Get the query (first argument)
QUERY="$1"

# Run the router with the query
echo "$QUERY" | python evals/run_router.py
