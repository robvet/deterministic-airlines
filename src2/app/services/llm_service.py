"""
LLM Service - Wrapper for Azure OpenAI calls.

This is the ONLY place in the app that talks to the language model.
Makes it easy to:
1. Set breakpoints to inspect prompts and responses
2. Swap models by changing config
3. Add logging/telemetry in one place

AUTHENTICATION:
- Uses DefaultAzureCredential (supports Azure CLI, Managed Identity, VS Code, etc.)
"""
import json
from typing import Type

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from pydantic import BaseModel

from ..config.llm_config import LLMConfig


class LLMService:
    """
    Simple wrapper around Azure OpenAI for making LLM calls.
    
    Supports both regular text responses and structured JSON responses.
    Uses DefaultAzureCredential for Entra ID authentication.
    """
    
    def __init__(self, config: LLMConfig):
        self._config = config
        self._deployment = config.azure_deployment
        self._classifier_deployment = config.classifier_deployment
        
        # Setup Azure AD token provider for Entra ID authentication
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), 
            "https://cognitiveservices.azure.com/.default"
        )
        
        # Create the Azure OpenAI client
        self._client = AzureOpenAI(
            api_version=config.azure_api_version,
            azure_endpoint=config.azure_endpoint,
            azure_ad_token_provider=token_provider,
        )
        
        print(f"[LLMService] Initialized")
        print(f"[LLMService]   Execution model: {self._deployment}")
        print(f"[LLMService]   Classifier model: {self._classifier_deployment}")
    
    def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: Type[BaseModel] | None = None,
        use_classifier_model: bool = False
    ) -> str | BaseModel:
        """
        Make a chat completion call to the LLM.
        
        Args:
            system_prompt: Instructions for the LLM (loaded from prompt template)
            user_message: The user's input
            response_model: Optional Pydantic model for structured JSON output
            use_classifier_model: If True, use the smaller/faster classifier model
            
        Returns:
            If response_model is None: returns the raw string response
            If response_model is provided: returns a validated Pydantic object
            
        DEBUGGING: Set a breakpoint here to see exactly what's sent to the LLM.
        """
        # Select deployment based on task type
        deployment = self._classifier_deployment if use_classifier_model else self._deployment
        print(f"[LLMService] Using deployment: {deployment}")
        
        # Build the messages list
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # If we want structured output, tell the LLM to return JSON
        if response_model is not None:
            # Add JSON instruction to system prompt
            schema_hint = f"\n\nYou MUST respond with valid JSON matching this schema:\n{response_model.model_json_schema()}"
            messages[0]["content"] = system_prompt + schema_hint
            
            # =============================================================
            # BREAKPOINT 9: LLM CALL - The actual API request
            # ---------------------------------------------------------
            # This is where we call Azure OpenAI. Set breakpoint here to:
            # - Inspect the full prompt being sent (messages)
            # - See which model is being used (deployment)
            # - Observe the round-trip time
            # =============================================================
            response = self._client.chat.completions.create(
                model=deployment,
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            # =============================================================
            # BREAKPOINT 10a: RAW LLM RESPONSE
            # ---------------------------------------------------------
            # Inspect the raw JSON string returned by the LLM.
            # This is BEFORE parsing - you can see exactly what the
            # model generated.
            # =============================================================
            raw_content = response.choices[0].message.content
            print(f"[LLMService] Raw LLM response: {raw_content[:200]}...")
            
            # =============================================================
            # BREAKPOINT 10b: JSON PARSING
            # ---------------------------------------------------------
            # Parse the raw string into a Python dict.
            # If the LLM returned invalid JSON, this will raise an error.
            # =============================================================
            parsed_json = json.loads(raw_content)
            
            # =============================================================
            # BREAKPOINT 10c: PYDANTIC VALIDATION
            # ---------------------------------------------------------
            # Validate the parsed dict against the Pydantic model.
            # This ensures the structure matches our schema:
            # - Required fields are present
            # - Types are correct (str, float, list, etc.)
            # - Constraints are met (e.g., confidence 0.0-1.0)
            # If validation fails, Pydantic raises ValidationError.
            # =============================================================
            validated_response = response_model.model_validate(parsed_json)
            print(f"[LLMService] Validated response type: {type(validated_response).__name__}")
            
            return validated_response
        
        else:
            # Simple text response
            response = self._client.chat.completions.create(
                model=deployment,
                messages=messages
            )
            
            return response.choices[0].message.content
