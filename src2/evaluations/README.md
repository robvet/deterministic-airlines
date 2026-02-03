# Evaluations

Azure AI Evaluation integration for Deterministic Airlines demo.

## Overview

This module uses the `azure-ai-evaluation` SDK to evaluate agent responses for:
- **Relevance** - Is the response relevant to the query?
- **Coherence** - Is the response logically coherent?
- **Groundedness** - Is the response grounded in the provided context?
- **Fluency** - Is the response well-written?

Results can be logged to Azure AI Foundry portal for tracking and comparison.

## Quick Start

```bash
# 1. Install dependencies
pip install azure-ai-evaluation

# 2. Start the backend (in one terminal)
cd src2
python run.py

# 3. Generate test data (in another terminal)
cd src2
python -m evaluations.generate_test_data

# 4. Run evaluation
python -m evaluations.run_eval --data evaluations/data/test_data.jsonl
```

## Before/After Workflow

```bash
# Run "before" evaluation
python -m evaluations.generate_test_data --output evaluations/data/before.jsonl
python -m evaluations.run_eval --data evaluations/data/before.jsonl --run-name "baseline"

# Make your improvements...

# Run "after" evaluation
python -m evaluations.generate_test_data --output evaluations/data/after.jsonl
python -m evaluations.run_eval --data evaluations/data/after.jsonl --run-name "with-improvements"

# Compare in Foundry portal
```

## Logging to Foundry Portal

Set these environment variables (or add to `.env`):

```env
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_AI_PROJECT_NAME=your-foundry-project-name
```

Then run with `--log-to-foundry`:

```bash
python -m evaluations.run_eval --data evaluations/data/test_data.jsonl --log-to-foundry
```

View results at: https://ai.azure.com → Your Project → Evaluation

## File Structure

```
evaluations/
├── __init__.py           # Package exports
├── generate_test_data.py # Runs agent, captures query/response pairs
├── run_eval.py           # Runs evaluators, logs to Foundry
├── README.md             # This file
├── data/                 # Test data files (JSONL)
│   └── test_data.jsonl
└── results/              # Evaluation results (JSON)
    └── eval_YYYYMMDD_HHMMSS.json
```

## Test Data Format

The generator outputs JSONL with this schema:

```json
{"query": "What is the baggage policy?", "response": "Our baggage policy...", "context": "Category: faq", "routed_to": "faq"}
```

## Custom Test Queries

Edit `TEST_QUERIES` in `generate_test_data.py` to customize test cases.
