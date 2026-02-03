"""
Prompt Template Service - Loads and populates prompt templates from external files.

Prompts are stored as plain text files in the prompts/ folder with {placeholder} syntax.
This separates prompt content from Python code, making it easy for workshop attendees
to modify prompts without touching code.

Benefits:
  - Prompts are version-controlled separately from logic
  - Non-developers can edit prompts
  - Easy A/B testing by swapping template files
  - Clear separation of concerns

Template syntax:
  - Use {placeholder_name} for variable substitution
  - Example: "Hello {customer_name}, how can I help with {topic}?"

Available templates (in prompts/ folder):
  - intent_prompt.txt: Intent classification with NER and prompt rewriting
  - faq_prompt.txt: FAQ tool system prompt with grounding data
"""
from pathlib import Path


class PromptTemplateService:
    """
    Loads prompt templates from external files and populates placeholders.
    
    Usage:
        template_service = PromptTemplateService()
        prompt = template_service.load("faq_prompt", {
            "customer_name": "John",
            "question": "What is your baggage policy?",
            "faq_knowledge_base": "..."
        })
    """
    
    def __init__(self, prompts_dir: Path | None = None):
        """
        Initialize the template service.
        
        Args:
            prompts_dir: Optional custom directory for templates.
                        Defaults to src2/prompts/
        """
        if prompts_dir is None:
            self._prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self._prompts_dir = prompts_dir
        
        available = self.list_templates()
        print(f"[PromptTemplateService] Initialized")
        print(f"[PromptTemplateService]   Template dir: {self._prompts_dir}")
        print(f"[PromptTemplateService]   Available: {available}")
    
    def load(self, template_name: str, variables: dict | None = None) -> str:
        """
        Load a prompt template and substitute variables.
        
        Args:
            template_name: Name of the template file (without .txt extension)
            variables: Dictionary of {placeholder: value} to substitute
            
        Returns:
            The formatted prompt string with all placeholders replaced
            
        Raises:
            FileNotFoundError: If template doesn't exist
            
        DEBUGGING: Set a breakpoint here to see the final prompt.
        """
        template_path = self._prompts_dir / f"{template_name}.txt"
        
        if not template_path.exists():
            raise FileNotFoundError(
                f"Prompt template not found: {template_path}\n"
                f"Available templates: {self.list_templates()}"
            )
        
        template = template_path.read_text(encoding="utf-8")
        
        # Substitute variables if provided
        if variables:
            for key, value in variables.items():
                template = template.replace(f"{{{key}}}", str(value))
        
        return template
    
    def list_templates(self) -> list[str]:
        """List all available template names."""
        return [p.stem for p in self._prompts_dir.glob("*.txt")]
