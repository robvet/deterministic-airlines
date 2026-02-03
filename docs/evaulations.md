# Install the new dependency
pip install azure-ai-evaluation

# 1. Start backend
cd src2
python run.py


# 2. Generate test data (runs 16 test queries through agent)
cd src2
python -m evaluations.generate_test_data

Will generate a file: src2/evaluations/data/test_data.jsonl


# 3. Run evaluation (local)
python -m evaluations.run_eval --data evaluations/data/test_data.jsonl

So, for the next step: python -m evaluations.run_eval --data evaluations/data/test_data.jsonl, what exactly is happens? Do I need to physically run a query?

No physical queries needed — the test data already contains the query/response pairs from when you ran generate_test_data.

What happens when you run run_eval:

Reads test_data.jsonl (already has 16 query + response pairs)
Sends each pair to Azure OpenAI as a "judge" call
The judge LLM scores each response on 4 metrics (1-5 scale):
Relevance: Does the response answer the query?
Coherence: Is the response logical/well-structured?
Groundedness: Is it grounded in the context?
Fluency: Is it well-written?
Outputs aggregate scores and per-row results to JSON

[Already done]                    [What you'll run now]
generate_test_data                run_eval
     │                                 │
     ▼                                 ▼
Your Agent ──► test_data.jsonl ──► Judge LLM ──► Scores
(16 queries)   (query+response)    (GPT-4o)      (JSON report)


# 4. Run evaluation + log to Foundry
python -m evaluations.run_eval --data evaluations/data/test_data.jsonl --log-to-fo

Exactly. Same evaluation as 3, but also uploads results to Foundry portal:

Command	What it does
python -m evaluations.run_eval --data ...	Runs evals locally, saves JSON report
python -m evaluations.run_eval --data ... --log-to-foundry	Same + uploads to Foundry portal
With --log-to-foundry:

Results appear in Azure AI Foundry portal → Evaluation tab
You can compare multiple runs side-by-side
Drill down into per-row scores

if   AZURE_SUBSCRIPTION_ID=your-sub-id
AZURE_RESOURCE_GROUP=your-rg
AZURE_AI_PROJECT_NAME=your-project

it will warn you

==============================================================















Yes, in this context "Foundry logging" specifically means evaluation results logging — sending your evaluation metrics to the Foundry portal so you can:

View evaluation runs in the portal UI
Compare before/after runs side-by-side
Drill down into per-row scores
Track improvements over time

| Feature | What it is | SDK/Tool |
|---------|-----------|----------|
| Foundry Evaluation Logging | Log eval metrics to portal | `azure-ai-evaluation` with `azure_ai_project` param |
| Foundry Tracing | Log request traces/spans to portal | `azure-ai-projects` SDK + OpenTelemetry |
| App Insights Telemetry | Log traces/metrics/logs | OpenTelemetry → App Insights (what we have now) |


AZURE_SUBSCRIPTION_ID=your-sub-id
AZURE_RESOURCE_GROUP=your-rg
AZURE_AI_PROJECT_NAME=your-project







Yes - several approaches depending on what you're evaluating:

Yes - several approaches depending on what you're evaluating:

LLM Output Quality

Promptfoo - Open source, test prompts against expected outputs, regression testing
Ragas - RAG-specific evaluation (faithfulness, relevance, context recall)
DeepEval - Unit testing for LLMs with metrics like hallucination, toxicity
Azure AI Evaluation SDK - Integrated with Azure AI Studio

Agent/Orchestration Evaluation

LangSmith - Trace agent runs, compare outputs, human feedback loops
Braintrust - Experiment tracking, A/B test prompts
Weights & Biases (W&B) - ML experiment tracking extended to LLMs

Key Metrics for Agentic Systems

Task completion rate
Tool call accuracy (right tool, right args)
Handoff precision (routed to correct agent)
Guardrail effectiveness (blocked bad inputs)
Latency per turn
Token efficiency

For your workshop, the most relevant would be:

Promptfoo - Test prompt changes don't regress behavior
Azure AI Evaluation - Since you're on Azure OpenAI already
Custom assertions - Validate tool calls match expected patterns
