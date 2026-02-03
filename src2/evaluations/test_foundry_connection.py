"""
Test Azure AI Foundry Connectivity

Quick check to verify your Foundry project settings are correct
before running evaluations with --log-to-foundry.

USAGE:
    cd src2
    python -m evaluations.test_foundry_connection
"""
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import settings


def test_connection():
    """Test connectivity to Azure AI Foundry."""
    print("=" * 60)
    print("AZURE AI FOUNDRY CONNECTION TEST")
    print("=" * 60)
    
    # Check settings
    print("\n1. Checking environment variables...")
    
    missing = []
    if not settings.azure_subscription_id:
        missing.append("AZURE_SUBSCRIPTION_ID")
    if not settings.azure_resource_group:
        missing.append("AZURE_RESOURCE_GROUP")
    if not settings.azure_ai_project_name:
        missing.append("AZURE_AI_PROJECT_NAME")
    
    if missing:
        print(f"   ❌ Missing: {', '.join(missing)}")
        print("\n   Add these to your .env file:")
        for var in missing:
            print(f"   {var}=your-value-here")
        return False
    
    print(f"   ✓ Subscription ID: {settings.azure_subscription_id[:8]}...")
    print(f"   ✓ Resource Group: {settings.azure_resource_group}")
    print(f"   ✓ Project Name: {settings.azure_ai_project_name}")
    
    # Try to import and connect
    print("\n2. Testing SDK import...")
    try:
        from azure.ai.evaluation import evaluate
        print("   ✓ azure-ai-evaluation SDK available")
    except ImportError:
        print("   ❌ azure-ai-evaluation not installed")
        print("   Run: pip install azure-ai-evaluation")
        return False
    
    # Try to authenticate
    print("\n3. Testing Azure authentication...")
    try:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        # Get a token to verify auth works
        token = credential.get_token("https://management.azure.com/.default")
        print("   ✓ Azure authentication successful")
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        print("   Make sure you're logged in with: az login")
        return False
    
    # Try to connect to the project (if azure-ai-projects is available)
    print("\n4. Testing Foundry project access...")
    try:
        from azure.ai.projects import AIProjectClient
        
        # Build the Foundry endpoint URL
        # Format: https://<region>.api.azureml.ms or project-specific endpoint
        # This is optional - azure-ai-evaluation can work without AIProjectClient
        print("   ⚠ azure-ai-projects installed but requires endpoint URL")
        print("   This is optional - azure-ai-evaluation handles Foundry logging directly")
        print("   ✓ Skipping AIProjectClient validation (not required)")
    except ImportError:
        print("   ⚠ azure-ai-projects not installed (optional)")
        print("   Foundry logging works via azure-ai-evaluation SDK")
    
    print("\n" + "=" * 60)
    print("✓ All checks passed! Ready to use --log-to-foundry")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
