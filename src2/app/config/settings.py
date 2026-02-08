"""
Centralized Application Settings

Uses Pydantic Settings to provide type-safe, validated configuration.
All settings are loaded from environment variables or .env file.

USAGE:
    from app.config.settings import settings
    
    endpoint = settings.azure_openai_endpoint
    port = settings.server_port
    conn_str = settings.application_insights_connection_string
"""
import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Find .env file - look in project root (parent of src2/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    
    ARCHITECTURE NOTES:
    - Required fields (no default) will fail fast at startup if missing
    - Optional fields (with default or | None) allow graceful degradation
    - validation_alias maps .env variable names to Python property names
    
    FOR C# DEVELOPERS:
    This is like IOptions<T> pattern in .NET, but with automatic
    environment variable binding. Think appsettings.json + env vars.
    """
    
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )
    
    # =========================================================================
    # Azure OpenAI (required for app to function)
    # =========================================================================
    azure_openai_endpoint: str = Field(
        default="",
        validation_alias="AZURE_OPENAI_ENDPOINT"
    )
    azure_openai_api_version: str = Field(
        default="2024-12-01-preview",
        validation_alias="AZURE_OPENAI_API_VERSION"
    )
    azure_openai_deployment: str = Field(
        default="gpt-5.2", 
        validation_alias="AZURE_OPENAI_INFERENCING_DEPLOYMENT"
    )
    azure_openai_classifier_deployment: str = Field(
        default="gpt-4.1-mini",
        validation_alias="AZURE_OPENAI_CLASSIFIER_DEPLOYMENT"
    )
    
    # Optional API key - if not set, uses DefaultAzureCredential (Entra ID)
    azure_openai_api_key: str | None = Field(
        default=None, 
        validation_alias="AZURE_OPENAI_API_KEY"
    )
    
    # =========================================================================
    # Application Insights / Telemetry (optional - app runs without it)
    # =========================================================================
    application_insights_connection_string: str | None = Field(
        default=None,
        validation_alias="APPLICATIONINSIGHTS_CONNECTION_STRING",
    )
    
    # =========================================================================
    # Application Metadata
    # =========================================================================
    app_name: str = Field(default="Deterministic Airlines Demo")
    environment: str = Field(default="dev", validation_alias="APP_ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    
    # =========================================================================
    # Server Configuration
    # =========================================================================
    server_host: str = Field(default="0.0.0.0", validation_alias="SERVER_HOST")
    server_port: int = Field(default=8000, validation_alias="SERVER_PORT")
    
    # =========================================================================
    # Orchestrator Confidence Thresholds (tunable via .env or UI)
    # =========================================================================
    confidence_threshold_execute: float = Field(
        default=0.7,
        validation_alias="CONFIDENCE_THRESHOLD_EXECUTE",
        description="Above this: execute the tool (default 0.7)"
    )
    confidence_threshold_clarify: float = Field(
        default=0.4,
        validation_alias="CONFIDENCE_THRESHOLD_CLARIFY",
        description="Above this but below execute: ask clarification (default 0.4)"
    )
    
    # =========================================================================
    # Conversation Context Settings (for multi-turn routing)
    # =========================================================================
    context_window_size: int = Field(
        default=3,
        validation_alias="CONTEXT_WINDOW_SIZE",
        description="Number of recent turns to include in classification context (default 3)"
    )
    
    # =========================================================================
    # Development Features (disabled by default for production safety)
    # =========================================================================
    open_browser: bool = Field(
        default=False, 
        validation_alias="OPEN_BROWSER",
        description="Auto-open browser on startup. Set OPEN_BROWSER=true for local dev."
    )
    
    # =========================================================================
    # Azure AI Foundry / Evaluations (optional - for logging evals to portal)
    # =========================================================================
    # NEW: Foundry endpoint URL (preferred for new Foundry projects)
    azure_ai_project_endpoint: str | None = Field(
        default=None,
        validation_alias="AZURE_AI_PROJECT_ENDPOINT",
        description="Foundry project endpoint URL (e.g., https://hub.services.ai.azure.com/api/projects/project-name)"
    )
    # LEGACY: Individual settings (fallback for older ML workspace style)
    azure_subscription_id: str | None = Field(
        default=None,
        validation_alias="AZURE_SUBSCRIPTION_ID",
        description="Azure subscription for Foundry project"
    )
    azure_resource_group: str | None = Field(
        default=None,
        validation_alias="AZURE_RESOURCE_GROUP",
        description="Resource group containing Foundry project"
    )
    azure_ai_project_name: str | None = Field(
        default=None,
        validation_alias="AZURE_AI_PROJECT_NAME",
        description="Foundry project name for evaluation logging"
    )
    azure_openai_eval_deployment: str = Field(
        default="gpt-4.1-mini",
        validation_alias="AZURE_OPENAI_EVAL_DEPLOYMENT",
        description="Model for evaluations (use model that accepts max_tokens)"
    )
    
    @property
    def azure_ai_project(self) -> str | dict | None:
        """
        Returns Foundry project config for azure-ai-evaluation SDK.
        
        Supports two formats:
        1. Endpoint URL string (new Foundry style) - preferred
        2. Dict with subscription/resource_group/project_name (legacy ML style)
        
        Returns None if not configured.
        """
        # Prefer endpoint URL (new Foundry approach)
        if self.azure_ai_project_endpoint:
            return self.azure_ai_project_endpoint
        
        # Fallback to dict format (legacy ML workspace approach)
        if all([self.azure_subscription_id, self.azure_resource_group, self.azure_ai_project_name]):
            return {
                "subscription_id": self.azure_subscription_id,
                "resource_group_name": self.azure_resource_group,
                "project_name": self.azure_ai_project_name,
            }
        return None


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached singleton of Settings.
    
    The @lru_cache ensures we only read .env once.
    Subsequent calls return the cached object.
    """
    return Settings()


# Singleton instance for easy import
settings = get_settings()
