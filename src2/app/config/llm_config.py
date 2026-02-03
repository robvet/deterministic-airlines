"""
LLM Configuration - Model and endpoint settings for Azure OpenAI.

Loads configuration from environment variables:
  - AZURE_OPENAI_ENDPOINT: Your Azure OpenAI resource endpoint
  - AZURE_OPENAI_INFERENCING_DEPLOYMENT: Deployment name for main model (e.g., gpt-5.2)
  - AZURE_OPENAI_CLASSIFIER_DEPLOYMENT: Deployment for fast classification (e.g., gpt-4.1-mini)
  - AZURE_OPENAI_API_VERSION: API version (default: 2024-12-01-preview)

Configuration is loaded from:
  1. .env file in the project root (one level up from src2/)
  2. Environment variables (override .env values)

Two models are configured:
  - azure_deployment: Main model for tool execution (reasoning, heavy lifting)
  - classifier_deployment: Fast model for intent classification (cheap, quick)

Authentication uses DefaultAzureCredential (Entra ID) - no API key needed.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parent of src2/)
# __file__ = src2/app/config/llm_config.py, so go up 4 levels
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


class LLMConfig:
    """
    Configuration for Azure OpenAI LLM connections.
    
    Two models are configured:
      - azure_deployment: Main model for tool execution (gpt-5.2)
      - classifier_deployment: Fast model for intent classification (gpt-4.1-mini)
    
    Usage:
        config = LLMConfig()
        config.validate()
        llm_service = LLMService(config)
    """
    
    def __init__(self):
        # Azure OpenAI endpoint (required)
        self.azure_endpoint: str | None = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        # Main model for tool execution (heavy lifting, reasoning)
        self.azure_deployment: str | None = os.getenv("AZURE_OPENAI_INFERENCING_DEPLOYMENT")
        
        # Fast model for intent classification (cheap, quick)
        self.classifier_deployment: str | None = os.getenv("AZURE_OPENAI_CLASSIFIER_DEPLOYMENT")
        
        # API version
        self.azure_api_version: str = os.getenv(
            "AZURE_OPENAI_API_VERSION", 
            "2024-12-01-preview"
        )
        
        # Optional API key (if not using DefaultAzureCredential)
        self.azure_api_key: str | None = os.getenv("AZURE_OPENAI_API_KEY")
        
        print(f"[LLMConfig] Initialized")
    
    def validate(self) -> None:
        """
        Validate that required settings are present.
        Call this at startup to fail fast if misconfigured.
        
        Raises:
            ValueError: If required settings are missing
        """
        if not self.azure_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
        if not self.azure_deployment:
            raise ValueError("AZURE_OPENAI_INFERENCING_DEPLOYMENT environment variable is required")
        if not self.classifier_deployment:
            raise ValueError("AZURE_OPENAI_CLASSIFIER_DEPLOYMENT environment variable is required")
        
        print(f"[LLMConfig] ✓ Validated")
        print(f"[LLMConfig]   Endpoint: {self.azure_endpoint}")
        print(f"[LLMConfig]   Execution model: {self.azure_deployment}")
        print(f"[LLMConfig]   Classifier model: {self.classifier_deployment}")
        print(f"[LLMConfig]   Auth: DefaultAzureCredential (Entra ID)")
