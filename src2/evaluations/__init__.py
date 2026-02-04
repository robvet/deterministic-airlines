"""
Evaluations Package

Tools for running Azure AI Evaluations on the Deterministic Airlines agent.

MODULES:
    generate_test_data - Runs agent against test queries, outputs JSONL
    run_eval - Runs evaluators and optionally logs to Foundry

QUICK START:
    # 1. Start the backend
    python run.py
    
    # 2. Generate test data (in another terminal)
    python -m evaluations.generate_test_data
    
    # 3. Run evaluation
    python -m evaluations.run_eval --data evaluations/data/test_data.jsonl
    
    # 4. (Optional) Log to Foundry portal
    python -m evaluations.run_eval --data evaluations/data/test_data.jsonl --log-to-foundry

FOUNDRY SETUP:
    Set these environment variables to enable Foundry logging:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_RESOURCE_GROUP
    - AZURE_AI_PROJECT_NAME
"""

from evaluations.generate_test_data import generate_test_data, TEST_QUERIES
from evaluations.run_eval import run_evaluation

__all__ = ["generate_test_data", "run_evaluation", "TEST_QUERIES"]

