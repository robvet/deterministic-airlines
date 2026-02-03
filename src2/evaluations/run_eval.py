"""
Evaluation Runner for Azure AI Evaluation SDK

Runs evaluators (Relevance, Coherence, Groundedness) on test data
and optionally logs results to Azure AI Foundry portal.

USAGE:
    cd src2
    
    # Run locally (no Foundry logging)
    python -m evaluations.run_eval --data evaluations/data/test_data.jsonl
    
    # Run and log to Foundry portal
    python -m evaluations.run_eval --data evaluations/data/test_data.jsonl --log-to-foundry
    
    # Before/After comparison workflow:
    python -m evaluations.run_eval --data test_before.jsonl --run-name "before-change"
    # ... make your improvements ...
    python -m evaluations.run_eval --data test_after.jsonl --run-name "after-change"
    # Compare in Foundry portal

REQUIREMENTS:
    pip install azure-ai-evaluation
    
    For Foundry logging, set these environment variables:
    - AZURE_SUBSCRIPTION_ID
    - AZURE_RESOURCE_GROUP  
    - AZURE_AI_PROJECT_NAME
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import settings


def run_evaluation(
    data_path: Path,
    output_path: Path | None = None,
    log_to_foundry: bool = False,
    run_name: str | None = None,
) -> dict:
    """
    Run evaluators on test data.
    
    Args:
        data_path: Path to JSONL file with query/response/context records
        output_path: Path to save evaluation results (auto-generated if None)
        log_to_foundry: Whether to log results to Foundry portal
        run_name: Name for this evaluation run (for Foundry tracking)
        
    Returns:
        Evaluation results dict
    """
    try:
        from azure.ai.evaluation import (
            evaluate,
            RelevanceEvaluator,
            CoherenceEvaluator,
            GroundednessEvaluator,
            FluencyEvaluator,
        )
    except ImportError:
        print("ERROR: azure-ai-evaluation not installed.")
        print("Run: pip install azure-ai-evaluation")
        sys.exit(1)
    
    # Validate data file exists
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        print("Generate test data first: python -m evaluations.generate_test_data")
        sys.exit(1)
    
    # Model config for judge (evaluator LLM)
    # Uses azure_openai_eval_deployment (gpt-4.1-mini by default)
    # because newer models (gpt-5.2) require max_completion_tokens but SDK uses max_tokens
    # When api_key is omitted, SDK uses DefaultAzureCredential (Entra ID)
    model_config = {
        "azure_endpoint": settings.azure_openai_endpoint,
        "azure_deployment": settings.azure_openai_eval_deployment,
        "api_version": settings.azure_openai_api_version,
        # No api_key = uses DefaultAzureCredential automatically
    }
    
    print("=" * 60)
    print("AZURE AI EVALUATION")
    print("=" * 60)
    print(f"Data file: {data_path}")
    print(f"Model endpoint: {settings.azure_openai_endpoint}")
    print(f"Eval deployment: {settings.azure_openai_eval_deployment}")
    print(f"Log to Foundry: {log_to_foundry}")
    
    # Foundry project config (optional)
    azure_ai_project = None
    if log_to_foundry:
        azure_ai_project = settings.azure_ai_project
        if not azure_ai_project:
            print("\nWARNING: Foundry logging requested but not configured.")
            print("Set these environment variables:")
            print("  - AZURE_SUBSCRIPTION_ID")
            print("  - AZURE_RESOURCE_GROUP")
            print("  - AZURE_AI_PROJECT_NAME")
            azure_ai_project = None
        else:
            print(f"Foundry project: {azure_ai_project['project_name']}")
    
    print("-" * 60)
    print("Initializing evaluators...")
    
    # Create evaluators
    evaluators = {
        "relevance": RelevanceEvaluator(model_config),
        "coherence": CoherenceEvaluator(model_config),
        "groundedness": GroundednessEvaluator(model_config),
        "fluency": FluencyEvaluator(model_config),
    }
    
    # Generate output path if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_suffix = f"_{run_name}" if run_name else ""
        output_path = Path(f"evaluations/results/eval_{timestamp}{run_suffix}.json")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Output: {output_path}")
    print("-" * 60)
    print("Running evaluation...")
    
    # Run evaluation
    result = evaluate(
        data=str(data_path),
        evaluators=evaluators,
        azure_ai_project=azure_ai_project,
        output_path=str(output_path),
    )
    
    print("-" * 60)
    print("RESULTS SUMMARY")
    print("-" * 60)
    
    # Extract metrics
    if hasattr(result, 'metrics') and result.metrics:
        for metric_name, value in result.metrics.items():
            if isinstance(value, float):
                print(f"  {metric_name}: {value:.3f}")
            else:
                print(f"  {metric_name}: {value}")
    
    print("-" * 60)
    print(f"✓ Results saved to: {output_path}")
    
    if log_to_foundry and azure_ai_project:
        print(f"✓ Results logged to Foundry project: {azure_ai_project['project_name']}")
        print("  View in portal: https://ai.azure.com → Evaluation")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Run Azure AI Evaluations on test data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate test data first
  python -m evaluations.generate_test_data
  
  # Run evaluation locally
  python -m evaluations.run_eval --data evaluations/data/test_data.jsonl
  
  # Run and log to Foundry portal
  python -m evaluations.run_eval --data evaluations/data/test_data.jsonl --log-to-foundry
  
  # Before/After comparison
  python -m evaluations.run_eval --data before.jsonl --run-name "baseline"
  python -m evaluations.run_eval --data after.jsonl --run-name "with-improvements"
        """
    )
    parser.add_argument(
        "--data", "-d",
        type=Path,
        default=Path("evaluations/data/test_data.jsonl"),
        help="Path to JSONL test data file"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output path for results (auto-generated if not provided)"
    )
    parser.add_argument(
        "--log-to-foundry",
        action="store_true",
        help="Log results to Azure AI Foundry portal"
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default=None,
        help="Name for this evaluation run (for tracking before/after)"
    )
    
    args = parser.parse_args()
    
    run_evaluation(
        data_path=args.data,
        output_path=args.output,
        log_to_foundry=args.log_to_foundry,
        run_name=args.run_name,
    )


if __name__ == "__main__":
    main()
