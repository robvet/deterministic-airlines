"""
Unit test for OrchestrationAgent FAQ flow.
"""
import unittest
from agent import OrchestrationAgent

class TestOrchestrationAgentFAQ(unittest.TestCase):
    def test_baggage_policy(self):
        agent = OrchestrationAgent()
        prompt = "What's the baggage policy?"
        print(f"Test input: {prompt}")
        response = agent.run(prompt)
        print(f"Agent output: {response}")
        self.assertIn("baggage", response.lower())
        self.assertIn("faq tool", response.lower())  # Should show tool was used (mock)

if __name__ == "__main__":
    unittest.main()
