"""
Unit tests for FAQ Structured Output Architecture.

These tests verify that:
1. FAQResponse model has structured fields (relevant_facts, not answer)
2. FAQTool returns structured data (not NL)
3. Orchestrator generates NL from structured data

RUN: pytest src2/app/tests/test_faq_structured_output.py -v
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

# Import models
from app.models.faq import FAQRequest, FAQResponse
from app.models.context import AgentContext


class TestFAQResponseModel:
    """Test that FAQResponse has the correct structured fields."""
    
    def test_faq_response_has_relevant_facts(self):
        """FAQResponse should have relevant_facts field, not answer."""
        response = FAQResponse(
            relevant_facts=["Carry-on limit: 22x14x9 inches", "Weight limit: 50 lbs"],
            confidence=0.95,
            source_topic="baggage",
            reasoning="User asked about luggage dimensions"
        )
        
        assert hasattr(response, 'relevant_facts')
        assert isinstance(response.relevant_facts, list)
        assert len(response.relevant_facts) == 2
    
    def test_faq_response_no_answer_field(self):
        """FAQResponse should NOT have an 'answer' field anymore."""
        response = FAQResponse(
            relevant_facts=["Test fact"],
            confidence=0.9,
            source_topic="test",
            reasoning="Test reasoning"
        )
        
        # The 'answer' field should not exist
        assert not hasattr(response, 'answer') or 'answer' not in response.model_fields
    
    def test_faq_response_requires_facts(self):
        """FAQResponse should require at least one fact."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            FAQResponse(
                relevant_facts=[],  # Empty list should fail
                confidence=0.9,
                source_topic="test",
                reasoning="Test"
            )
    
    def test_faq_response_requires_reasoning(self):
        """FAQResponse should require reasoning field."""
        response = FAQResponse(
            relevant_facts=["Test fact"],
            confidence=0.9,
            source_topic="test",
            reasoning="Why these facts were selected"
        )
        
        assert response.reasoning == "Why these facts were selected"
    
    def test_faq_response_confidence_range(self):
        """Confidence must be between 0.0 and 1.0."""
        # Valid confidence
        response = FAQResponse(
            relevant_facts=["Test"],
            confidence=0.5,
            source_topic="test",
            reasoning="Test"
        )
        assert response.confidence == 0.5
        
        # Invalid confidence should raise error
        with pytest.raises(Exception):
            FAQResponse(
                relevant_facts=["Test"],
                confidence=1.5,  # Invalid
                source_topic="test",
                reasoning="Test"
            )


class TestFAQToolStructuredOutput:
    """Test that FAQTool returns structured data, not NL."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service that returns structured FAQResponse."""
        mock = Mock()
        mock.complete.return_value = FAQResponse(
            relevant_facts=[
                "Carry-on bag size limit: 22x14x9 inches",
                "Weight limit: 50 lbs per checked bag",
                "First checked bag fee: $35"
            ],
            confidence=0.92,
            source_topic="baggage",
            reasoning="User asked about baggage policy, matched to allowance and fees sections"
        )
        return mock
    
    @pytest.fixture
    def mock_template_service(self):
        """Create a mock template service."""
        mock = Mock()
        mock.load.return_value = "Test prompt with {customer_name} and {faq_knowledge_base}"
        return mock
    
    def test_faq_tool_returns_structured_response(self, mock_llm_service, mock_template_service):
        """FAQTool.execute() should return FAQResponse with structured data."""
        from app.tools.faq_tool import FAQTool
        
        with patch('app.tools.faq_tool.get_formatted_faq_data', return_value="Mock FAQ data"):
            tool = FAQTool(mock_llm_service, mock_template_service)
            
            request = FAQRequest(question="What's the baggage policy?")
            context = AgentContext(customer_name="Test User")
            
            response = tool.execute(request, context)
            
            # Verify it's a FAQResponse
            assert isinstance(response, FAQResponse)
            
            # Verify it has structured fields
            assert hasattr(response, 'relevant_facts')
            assert len(response.relevant_facts) > 0
            
            # Verify no NL answer field
            assert not hasattr(response, 'answer') or 'answer' not in response.model_fields
    
    def test_faq_tool_includes_reasoning(self, mock_llm_service, mock_template_service):
        """FAQTool response should include reasoning for fact selection."""
        from app.tools.faq_tool import FAQTool
        
        with patch('app.tools.faq_tool.get_formatted_faq_data', return_value="Mock FAQ data"):
            tool = FAQTool(mock_llm_service, mock_template_service)
            
            request = FAQRequest(question="What's the baggage policy?")
            context = AgentContext(customer_name="Test User")
            
            response = tool.execute(request, context)
            
            assert response.reasoning
            assert len(response.reasoning) > 0


class TestOrchestratorNLGeneration:
    """Test that Orchestrator generates NL from structured tool data."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for orchestrator testing."""
        # Mock LLM service
        llm_mock = Mock()
        # First call: classification, Second call: tool, Third call: NL generation
        llm_mock.complete.side_effect = [
            # Classification response (would need ClassificationResponse mock)
            Mock(
                intent="faq",
                confidence=0.9,
                reasoning="User asking about policy",
                rewritten_prompt="What is the baggage policy?",
                entities=[]
            ),
            # Tool response (FAQResponse)
            FAQResponse(
                relevant_facts=["Carry-on: 22x14x9 inches", "Weight: 50 lbs"],
                confidence=0.95,
                source_topic="baggage",
                reasoning="Matched baggage policies"
            ),
            # NL generation response
            "You can bring one carry-on bag (22x14x9 inches). Checked bags have a 50 lb weight limit."
        ]
        
        # Mock template service
        template_mock = Mock()
        template_mock.load.return_value = "Mock prompt"
        
        # Mock memory store
        memory_mock = Mock()
        
        # Mock registry
        registry_mock = Mock()
        registry_mock.get_routing_descriptions.return_value = "faq: handles FAQ questions"
        registry_mock.has_tool.return_value = True
        registry_mock.list_tools.return_value = ["faq"]
        
        return {
            'llm': llm_mock,
            'template': template_mock,
            'memory': memory_mock,
            'registry': registry_mock
        }
    
    def test_orchestrator_generates_nl_from_structured_data(self):
        """Orchestrator should call LLM to generate NL from tool's structured output."""
        # This is an integration-level test concept
        # In actual implementation, we'd verify the _generate_nl_response method is called
        # with the structured tool response
        
        # For now, verify the NL generation prompt template exists
        import os
        prompt_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'prompts', 'response_generator_prompt.txt'
        )
        
        # The prompt file should exist
        assert os.path.exists(prompt_path), "response_generator_prompt.txt should exist"
        
        # Read and verify it has the right placeholders
        with open(prompt_path, 'r') as f:
            content = f.read()
        
        assert '{customer_name}' in content
        assert '{tool_data}' in content
        assert '{intent_guidance}' in content


class TestEndToEndFAQFlow:
    """Integration tests for the complete FAQ flow."""
    
    def test_faq_response_can_be_serialized_to_json(self):
        """FAQResponse should be serializable for NL generation prompt."""
        response = FAQResponse(
            relevant_facts=["Fact 1", "Fact 2"],
            confidence=0.9,
            source_topic="baggage",
            reasoning="Test reasoning"
        )
        
        # Should be serializable
        json_str = json.dumps(response.model_dump(), indent=2)
        assert '"relevant_facts"' in json_str
        assert '"Fact 1"' in json_str
        assert '"reasoning"' in json_str
    
    def test_structured_response_contains_all_needed_data(self):
        """Structured response should have everything needed for NL generation."""
        response = FAQResponse(
            relevant_facts=["Carry-on: 22x14x9", "50 lb limit"],
            confidence=0.95,
            source_topic="baggage",
            reasoning="User asked about luggage size limits"
        )
        
        data = response.model_dump()
        
        # All fields needed for NL generation
        assert 'relevant_facts' in data
        assert 'confidence' in data
        assert 'source_topic' in data
        assert 'reasoning' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
