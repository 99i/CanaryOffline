import asyncio
import os
import sys
from typing import Optional, Dict, Any
import json

# Try to import ollama, if not available, provide installation instructions
try:
    import ollama
except ImportError:
    print("Ollama package not found. Please install it using:")
    print("pip install ollama")
    sys.exit(1)
    
class QuestionGenerator:
    """
    A specialized question generator using Gemma 3:1b-it-qat model.
    Generates thoughtful questions based on topic and conversation context.
    """
    
    def __init__(self, model_name: str = "gemma3:1b-it-qat"):
        """
        Initialize the question generator.
        
        Args:
            model_name: The Ollama model to use for question generation
        """
        self.model_name = model_name
        self.last_response = ""
        
    def generate_question(self, topic: str, last_response: str = "", max_tokens: int = 300, temperature: float = 0.8) -> str:
        """
        Generate a thoughtful question based on the topic and last Canary response.
        
        Args:
            topic: The current topic being studied
            last_response: The last response from Canary (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness
            
        Returns:
            A thoughtful question to help the user understand the topic better
        """
        if not topic:
            return "Please set a topic first."
            
        # Create a focused prompt for question generation
        question_prompt = f"""You are Canary, a learning assistant focused on {topic}. 

Based on the topic '{topic}' and the last conversation context, generate a thoughtful and engaging question that will help the user deepen their understanding of {topic}.

The question should:
- Be specific to {topic}
- Encourage critical thinking
- Help identify knowledge gaps
- Be appropriate for the user's learning level
- Be concise and to the point
- Be deep and thought-provoking

Topic: {topic}
Last response context: {last_response if last_response else 'No previous context'}

Generate a single, focused question:"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": question_prompt
                    }
                ],
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            return f"Error generating question: {str(e)}"
    
    def generate_deep_question(self, topic: str, last_response: str = "", max_tokens: int = 400, temperature: float = 0.9) -> str:
        """
        Generate a deep, analytical question that requires critical thinking.
        
        Args:
            topic: The current topic being studied
            last_response: The last response from Canary (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness
            
        Returns:
            A deep analytical question
        """
        if not topic:
            return "Please set a topic first."
            
        deep_question_prompt = f"""You are Canary, a learning assistant focused on {topic}. 

Generate a deep, analytical question that will challenge the user's understanding of {topic}. This should be a question that:

- Requires critical thinking and analysis
- Connects different concepts within {topic}
- Asks for real-world applications or implications
- Encourages the user to think beyond surface-level understanding
- Could lead to a deeper discussion about {topic}
- Is thought-provoking and engaging

Topic: {topic}
Last response context: {last_response if last_response else 'No previous context'}

Generate a single, deep analytical question:"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": deep_question_prompt
                    }
                ],
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            return f"Error generating deep question: {str(e)}"
    
    def generate_follow_up_question(self, topic: str, user_explanation: str, last_response: str = "", max_tokens: int = 250, temperature: float = 0.7) -> str:
        """
        Generate a follow-up question based on the user's explanation.
        
        Args:
            topic: The current topic being studied
            user_explanation: What the user just explained
            last_response: The last response from Canary (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness
            
        Returns:
            A follow-up question based on the user's explanation
        """
        if not topic:
            return "Please set a topic first."
            
        follow_up_prompt = f"""You are Canary, a learning assistant focused on {topic}. 

The user just explained something about {topic}. Based on their explanation, generate a follow-up question that will help them:

- Clarify any unclear points in their explanation
- Explore related aspects they might have missed
- Connect their explanation to broader concepts in {topic}
- Apply their understanding to practical scenarios
- Think more deeply about the implications

User's explanation: {user_explanation}
Topic: {topic}
Last response context: {last_response if last_response else 'No previous context'}

Generate a single, focused follow-up question:"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": follow_up_prompt
                    }
                ],
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            return f"Error generating follow-up question: {str(e)}"
    
    def get_available_models(self) -> list:
        """
        Get list of available Ollama models.
        
        Returns:
            List of available model names
        """
        try:
            models = ollama.list()
            return [model['name'] for model in models['models']]
        except Exception as e:
            return [f"Error getting models: {str(e)}"]
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "last_response": self.last_response[:100] + "..." if self.last_response and len(self.last_response) > 100 else self.last_response
        }
