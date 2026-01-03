#!/bin/bash
# Quick interactive test
cd /Users/james.cahoon/projects/clarvis
echo "How many unread emails do I have?" | python -m clarvis_agents.gmail_agent 2>&1 | head -50
