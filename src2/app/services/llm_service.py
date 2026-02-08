"""
LLM Service - Wrapper for Azure OpenAI calls.

This is the ONLY place in the app that talks to the language model.
Makes it easy to:
1. Set breakpoints to inspect prompts and responses
2. Swap models by changing config
3. Add logging/telemetry in one place

AUTHENTICATION:
- Uses DefaultAzureCredential (supports Azure CLI, Managed Identity, VS Code, etc.)

ERROR HANDLING:
- Validation errors trigger one retry
- If retry fails, raises LLMValidationError with details
- Caller (Orchestrator) can catch and return user-friendly message
"""
import json
from typing import Type

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from pydantic import BaseModel, ValidationError

from ..config.llm_config import LLMConfig


class LLMValidationError(Exception):
    """
    Raised when LLM response fails validation after retry.
    
    Contains details about what failed so caller can return
    a meaningful error message to the user.
    """
    def __init__(self, message: str, validation_errors: list[dict], raw_response: str):
        super().__init__(message)
        self.validation_errors = validation_errors
        self.raw_response = raw_response
    
    def get_error_summary(self) -> str:
        """Return a user-friendly summary of what went wrong."""
        if not self.validation_errors:
            return "Response format was invalid"
        
        # Extract field names and error types
        issues = []
        for err in self.validation_errors:
            field = ".".join(str(loc) for loc in err.get("loc", ["unknown"]))
            msg = err.get("msg", "invalid")
            issues.append(f"{field}: {msg}")
        
        return "; ".join(issues[:3])  # Limit to first 3 issues


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
        
        # Choose authentication method: API key or DefaultAzureCredential
        if config.azure_api_key:
            # Use API key authentication
            self._client = AzureOpenAI(
                api_version=config.azure_api_version,
                azure_endpoint=config.azure_endpoint,
                api_key=config.azure_api_key,
            )
            auth_method = "API Key"
        else:
            # Use DefaultAzureCredential (Entra ID) authentication
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), 
                "https://cognitiveservices.azure.com/.default"
            )
            self._client = AzureOpenAI(
                api_version=config.azure_api_version,
                azure_endpoint=config.azure_endpoint,
                azure_ad_token_provider=token_provider,
            )
            auth_method = "DefaultAzureCredential (Entra ID)"
        
        print(f"[LLMService] Initialized")
        print(f"[LLMService]   Execution model: {self._deployment}")
        print(f"[LLMService]   Classifier model: {self._classifier_deployment}")
        print(f"[LLMService]   Auth: {auth_method}")
    
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
            # =============================================================
            # SCHEMA_HINT: Inject Pydantic model's JSON Schema into prompt
            # ---------------------------------------------------------
            # model_json_schema() converts the Pydantic model into a formal
            # JSON Schema specification. This tells the LLM exactly:
            #   - Field names and types (string, number, array, etc.)
            #   - Required vs optional fields
            #   - Validation constraints (min/max, minLength, etc.)
            #   - Field descriptions
            #
            # Each response_model produces a DIFFERENT schema:
            #   - FAQResponse → {relevant_facts: [], confidence: 0-1, ...}
            #   - ClassificationResponse → {intent: str, entities: [], ...}
            #   - FlightStatusResponse → {found: bool, status: str, ...}
            #
            # This is how we get intent-specific structured outputs using
            # one generic complete() method.
            # =============================================================
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
            # PARSE AND VALIDATE WITH RETRY
            # ---------------------------------------------------------
            # Try to parse and validate. If it fails, retry once.
            # If retry also fails, raise LLMValidationError with details.
            # =============================================================
            max_attempts = 2
            last_error = None
            last_raw = raw_content
            
            for attempt in range(max_attempts):
                try:
                    # Attempt to parse JSON
                    try:
                        parsed_json = json.loads(last_raw)
                    except json.JSONDecodeError as e:
                        raise ValidationError.from_exception_data(
                            "JSON parse error",
                            [{"type": "json_invalid", "loc": ("response",), "msg": str(e)}]
                        )
                    
                    # Validate against Pydantic model
                    validated_response = response_model.model_validate(parsed_json)
                    print(f"[LLMService] Validated response type: {type(validated_response).__name__}")
                    return validated_response
                    
                except ValidationError as e:
                    last_error = e
                    print(f"[LLMService] Validation failed (attempt {attempt + 1}/{max_attempts}): {e.error_count()} errors")
                    print(f"[LLMService] Validation errors: {e.errors()}")
                    print(f"[LLMService] Raw response was: {last_raw}")
                    
                    if attempt < max_attempts - 1:
                        # Retry: make another LLM call
                        print(f"[LLMService] Retrying LLM call...")
                        retry_response = self._client.chat.completions.create(
                            model=deployment,
                            messages=messages,
                            response_format={"type": "json_object"}
                        )
                        last_raw = retry_response.choices[0].message.content
                        print(f"[LLMService] Retry response: {last_raw[:200]}...")
            
            # If we get here, all attempts failed
            error_details = last_error.errors() if last_error else []
            print(f"[LLMService] All attempts failed. Raising LLMValidationError.")
            raise LLMValidationError(
                message=f"LLM response failed validation after {max_attempts} attempts",
                validation_errors=error_details,
                raw_response=last_raw
            )
        
        else:
            # Simple text response
            response = self._client.chat.completions.create(
                model=deployment,
                messages=messages
            )
            
            return response.choices[0].message.content
