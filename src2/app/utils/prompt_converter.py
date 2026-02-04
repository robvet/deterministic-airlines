"""
Chain of Thought Prompt Converter

Converts plain prompts into Chain of Thought prompts that encourage
step-by-step reasoning from the LLM.

USAGE:
    from app.utils.prompt_converter import PromptConverter
    
    converter = PromptConverter()
    cot_prompt = converter.convert("What is the capital of France?")
    # Returns: "What is the capital of France? Let's think through this step by step..."
"""
from ..config.llm_config import LLMConfig
from ..services.llm_service import LLMService
from ..services.prompt_template_service import PromptTemplateService


class PromptConverter:
    """
    Converts plain prompts into Chain of Thought prompts.
    
    Takes a simple question or instruction and transforms it into
    a prompt that encourages the LLM to reason step-by-step.
    
    System prompt is loaded from: prompts/cot_converter_prompt.txt
    """

    def __init__(self, llm_service: LLMService | None = None):
        """
        Initialize the prompt converter.
        
        Args:
            llm_service: Optional LLMService instance. If not provided, creates one.
        """
        if llm_service:
            self._llm = llm_service
        else:
            config = LLMConfig()
            self._llm = LLMService(config)
        
        # Load system prompt from external file
        self._template_service = PromptTemplateService()
        self._system_prompt = self._template_service.load("cot_converter_prompt")
    
    def convert_with_reasoning(self, prompt: str, use_inference_model: bool = False) -> tuple[str, str]:
        """
        Convert a plain prompt into a Chain of Thought prompt.
        
        Args:
            prompt: The original simple prompt
            use_inference_model: If True, uses the main inference model (gpt-4o) for higher quality.
                                 If False (default), uses the faster classifier model (gpt-4o-mini).
            
        Returns:
            Tuple of (cot_prompt, thinking_process)
        """
        if not prompt or not prompt.strip():
            return "", ""
        
        # Call LLM to convert the prompt
        response = self._llm.complete(
            system_prompt=self._system_prompt,
            user_message=prompt,
            use_classifier_model=not use_inference_model  # Invert: inference model = NOT classifier
        )
        
        # Parse the response - extract thinking and converted prompt
        thinking = ""
        converted = response
        
        if "<thinking>" in response and "</thinking>" in response:
            start = response.find("<thinking>") + len("<thinking>")
            end = response.find("</thinking>")
            thinking = response[start:end].strip()
            converted = response[end + len("</thinking>"):].strip()
        
        return converted, thinking
    
    def convert(self, prompt: str, use_inference_model: bool = False) -> str:
        """
        Convert a prompt and return only the CoT version.
        
        Args:
            prompt: The original simple prompt
            use_inference_model: If True, uses gpt-4o; if False (default), uses gpt-4o-mini
            
        Returns:
            The Chain of Thought enhanced prompt
        """
        converted, _ = self.convert_with_reasoning(prompt, use_inference_model=use_inference_model)
        return converted
