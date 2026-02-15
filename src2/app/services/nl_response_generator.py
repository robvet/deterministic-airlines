"""
NL Response Generator - Converts structured tool data to natural language.

Single responsibility: Take structured data from tools and generate
user-facing natural language responses via LLM.
"""

import json
from ..models.context import AgentContext
from .llm_service import LLMService
from .prompt_template_service import PromptTemplateService


DEFAULT_NL_GUIDANCE = """Provide a helpful, professional response based on the data provided.
Include all relevant information from the tool response.
"""


class NLResponseGenerator:
    """
    Generates natural language responses from structured tool data.
    
    This is the SINGLE POINT of NL generation in the system.
    Tools return structured data, this class converts to NL.
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        template_service: PromptTemplateService
    ):
        self._llm = llm_service
        self._templates = template_service
    
    def generate(
        self,
        tool_response,
        intent: str,
        original_question: str,
        context: AgentContext
    ) -> str:
        """
        Generate natural language response from structured tool data.
        
        Args:
            tool_response: Structured response from the tool (Pydantic model)
            intent: The classified intent (e.g., "faq", "flight_status")
            original_question: The user's original question
            context: Conversation context
            
        Returns:
            Natural language response string
        """
        print(f"[NLResponseGenerator] Generating for intent: {intent}")
        
        # Serialize tool response to JSON
        if hasattr(tool_response, 'model_dump'):
            tool_data_dict = tool_response.model_dump()
        else:
            tool_data_dict = dict(tool_response)
        
        tool_data_json = json.dumps(tool_data_dict, indent=2, default=str)
        
        # Load intent-specific guidance (decoupled - loaded from file)
        guidance_template_name = f"{intent}_nl_guidance"
        try:
            intent_guidance = self._templates.load(guidance_template_name, {})
        except FileNotFoundError:
            print(f"[NLResponseGenerator] No guidance file for '{intent}', using default")
            intent_guidance = DEFAULT_NL_GUIDANCE
        
        # Build prompt
        prompt = self._templates.load("response_generator_prompt", {
            "customer_name": context.customer_name,
            "original_question": original_question,
            "tool_name": intent,
            "tool_data": tool_data_json,
            "intent_guidance": intent_guidance
        })
        
        # Generate NL
        nl_response = self._llm.complete(
            system_prompt=prompt,
            user_message=f"Generate a response for: {original_question}"
        )
        
        print(f"[NLResponseGenerator] Complete ({len(nl_response)} chars)")
        return nl_response
    
    def generate_combined(
        self,
        tool_results: list[tuple],
        original_question: str,
        context: AgentContext
    ) -> str:
        """
        Generate ONE coherent NL response from multiple tool results.
        
        Called when the reflection loop executed 2+ tools.
        Combines all structured data and intent-specific guidance into
        a single LLM call to produce a unified, non-fractured response.
        
        Args:
            tool_results: List of (tool_response, ClassificationResponse) tuples
            original_question: The user's original question
            context: Conversation context
            
        Returns:
            Single natural language response string
        """
        print(f"[NLResponseGenerator] Generating combined response for {len(tool_results)} tool results")
        
        # Build combined tool data and guidance
        combined_sections = []
        combined_guidance = []
        
        for i, (tool_response, cls) in enumerate(tool_results, 1):
            # Serialize each tool response
            if hasattr(tool_response, 'model_dump'):
                tool_data_dict = tool_response.model_dump()
            else:
                tool_data_dict = dict(tool_response)
            
            tool_data_json = json.dumps(tool_data_dict, indent=2, default=str)
            combined_sections.append(
                f"### Result {i}: {cls.intent}\n{tool_data_json}"
            )
            
            # Load intent-specific guidance
            guidance_template_name = f"{cls.intent}_nl_guidance"
            try:
                guidance = self._templates.load(guidance_template_name, {})
                combined_guidance.append(f"For {cls.intent}:\n{guidance}")
            except FileNotFoundError:
                combined_guidance.append(f"For {cls.intent}:\n{DEFAULT_NL_GUIDANCE}")
        
        all_tool_data = "\n\n".join(combined_sections)
        all_guidance = "\n\n".join(combined_guidance)
        
        # Build prompt using the combined template
        prompt = self._templates.load("response_generator_combined_prompt", {
            "customer_name": context.customer_name,
            "original_question": original_question,
            "tool_data": all_tool_data,
            "intent_guidance": all_guidance
        })
        
        # Generate single coherent NL response
        nl_response = self._llm.complete(
            system_prompt=prompt,
            user_message=f"Generate a response for: {original_question}"
        )
        
        print(f"[NLResponseGenerator] Combined complete ({len(nl_response)} chars)")
        return nl_response
