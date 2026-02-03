"""
Test Data Generator for Evaluations

Runs your agent against test queries and captures query/response/context
for evaluation by azure-ai-evaluation SDK.

USAGE:
    cd src2
    python -m evaluations.generate_test_data
    
    # Or with custom output path:
    python -m evaluations.generate_test_data --output ./my_test_data.jsonl

OUTPUT FORMAT (JSONL):
    {"query": "...", "response": "...", "context": "...", "routed_to": "..."}

The output file can be fed directly to the evaluation runner.
"""
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime


# Test queries covering all tool categories
TEST_QUERIES = [
    # FAQ queries
    {"query": "What is the baggage policy?", "category": "faq"},
    {"query": "Is there WiFi on flights?", "category": "faq"},
    {"query": "What time should I arrive at the airport?", "category": "faq"},
    {"query": "Do you serve meals on domestic flights?", "category": "faq"},
    
    # Booking queries
    {"query": "I want to book flight DA100 to Los Angeles", "category": "book_flight"},
    {"query": "Book me on flight DA200 to Chicago", "category": "book_flight"},
    
    # Cancellation queries
    {"query": "Cancel my booking IR-D204", "category": "cancel_flight"},
    {"query": "I need to cancel reservation LL0EZ6", "category": "cancel_flight"},
    
    # Flight status queries
    {"query": "What is the status of flight PA441?", "category": "flight_status"},
    {"query": "Is flight DA100 on time?", "category": "flight_status"},
    
    # Seat queries
    {"query": "I'd like to change to a window seat", "category": "seat"},
    {"query": "Can I get an aisle seat please?", "category": "seat"},
    
    # Baggage queries
    {"query": "My bag is missing, I need to file a claim", "category": "baggage"},
    {"query": "How do I track my lost luggage?", "category": "baggage"},
    
    # Compensation queries
    {"query": "My flight was delayed 5 hours, I need compensation", "category": "compensation"},
    {"query": "I missed my connection, what are my options?", "category": "compensation"},
]


def call_agent(query: str, api_url: str = "http://localhost:8000") -> dict:
    """
    Call the agent API and return response with metadata.
    
    Args:
        query: User query to send to agent
        api_url: Base URL of FastAPI backend
        
    Returns:
        Dict with response and routing metadata
    """
    try:
        response = requests.post(
            f"{api_url}/chat",
            json={"message": query, "customer_name": "Test User"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "response": data.get("answer", ""),
            "routed_to": data.get("routed_to", "unknown"),
            "confidence": data.get("confidence", 0.0),
            "rewritten_input": data.get("rewritten_input", query),
        }
    except Exception as e:
        return {
            "success": False,
            "response": f"Error: {e}",
            "routed_to": "error",
            "confidence": 0.0,
            "rewritten_input": query,
        }


def generate_test_data(
    output_path: Path,
    api_url: str = "http://localhost:8000",
    queries: list[dict] | None = None
) -> None:
    """
    Generate test data JSONL file by running queries through the agent.
    
    Args:
        output_path: Path to output JSONL file
        api_url: Base URL of FastAPI backend
        queries: List of query dicts (uses TEST_QUERIES if None)
    """
    queries = queries or TEST_QUERIES
    results = []
    
    print(f"Generating test data from {len(queries)} queries...")
    print(f"API URL: {api_url}")
    print("-" * 60)
    
    for i, item in enumerate(queries, 1):
        query = item["query"]
        expected_category = item["category"]
        
        print(f"[{i}/{len(queries)}] {query[:50]}...", end=" ", flush=True)
        
        result = call_agent(query, api_url)
        
        if result["success"]:
            print(f"[OK] -> {result['routed_to']}")
        else:
            print(f"[FAIL] Error")
        
        # Format for azure-ai-evaluation
        eval_record = {
            "query": query,
            "response": result["response"],
            "context": f"Category: {expected_category}. Customer: Test User.",
            # Metadata for analysis (no timestamp - causes pandas serialization issues)
            "routed_to": result["routed_to"],
            "expected_category": expected_category,
            "confidence": result["confidence"],
        }
        results.append(eval_record)
    
    # Write JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in results:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print("-" * 60)
    print(f"[OK] Generated {len(results)} records -> {output_path}")
    
    # Summary stats
    successful = sum(1 for r in results if r["routed_to"] != "error")
    correct_routing = sum(1 for r in results if r["routed_to"] == r["expected_category"])
    print(f"  Successful: {successful}/{len(results)}")
    print(f"  Correct routing: {correct_routing}/{len(results)}")


def main():
    parser = argparse.ArgumentParser(description="Generate test data for evaluations")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("evaluations/data/test_data.jsonl"),
        help="Output JSONL file path"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="FastAPI backend URL"
    )
    
    args = parser.parse_args()
    
    generate_test_data(args.output, args.api_url)


if __name__ == "__main__":
    main()
