"""
LLM Service - LiteLLM Version (FOR FUTURE REFERENCE)

This version uses LiteLLM for multi-provider support (Azure, OpenAI, Anthropic, etc.)
Currently not used - the workshop uses Azure OpenAI directly.

To use this version:
1. Replace services/llm_service.py with this file
2. pip install litellm
3. Set appropriate environment variables for your provider

LITELLM MODEL STRINGS:
- Azure OpenAI: "azure/<deployment-name>"
- OpenAI direct: "gpt-4o" or "gpt-4o-mini"
- Anthropic: "claude-3-opus-20240229"
"""
import json
import os
from typing import Type

from litellm import completion
from pydantic import BaseModel

from ..config.llm_config import LLMConfig


class LLMService:
    """
    LiteLLM-based wrapper for multi-provider LLM calls.
    """
    
    def __init__(self, settings: Settings):
        self._settings = settings
        self._model = settings.model_name  # e.g., "azure/gpt-4o" or "gpt-4o"
        
        # Configure LiteLLM for Azure if using Azure
        if settings.model_name.startswith("azure/"):
            os.environ["AZURE_API_KEY"] = settings.azure_api_key or ""
            os.environ["AZURE_API_BASE"] = settings.azure_endpoint or ""
            os.environ["AZURE_API_VERSION"] = settings.azure_api_version
    
    def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: Type[BaseModel] | None = None
    ) -> str | BaseModel:
        """
        Make a chat completion call using LiteLLM.
        
        Args:
            system_prompt: Instructions for the LLM
            user_message: The user's input
            response_model: Optional Pydantic model for structured JSON output
            
        Returns:
            If response_model is None: returns the raw string response
            If response_model is provided: returns a validated Pydantic object
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if response_model is not None:
            # Add JSON schema hint to system prompt
            schema_hint = f"\n\nYou MUST respond with valid JSON matching this schema:\n{response_model.model_json_schema()}"
            messages[0]["content"] = system_prompt + schema_hint
            
            # Call LLM with JSON mode
            response = completion(
                model=self._model,
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            # Parse and validate
            raw_content = response.choices[0].message.content
            parsed_json = json.loads(raw_content)
            validated_response = response_model.model_validate(parsed_json)
            
            return validated_response
        
        else:
            response = completion(
                model=self._model,
                messages=messages
            )
            
            return response.choices[0].message.content
