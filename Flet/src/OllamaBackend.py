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
    
base_model="gemma3n:e2b-it-q4_K_M"
class CanaryTopicModel:
    """
    A model class that specializes in a given topic using the Canary approach.
    Instead of providing answers, it encourages users to explain topics to it,
    helping them learn through guided questioning and exploration.
    """
   
    
    def __init__(self, base_model: str = base_model, topic: Optional[str] = None):
        """
        Initialize the Canary topic model.
        
        Args:
            base_model: The base Ollama model to use
            topic: The topic to specialize in for learning conversations
        """
        self.base_model = base_model
        self.topic = topic
        self.system_prompt = self._create_system_prompt(topic) if topic else None
        
    def _create_system_prompt(self, topic: str) -> str:
        """
        Create a specialized system prompt for the given topic using the Canary approach.
        
        Args:
            topic: The topic to specialize in
            
        Returns:
            A specialized system prompt that encourages user explanation
        """
        return f"""You are Canary, a curious and supportive conversational partner specialized in {topic}. Your goal is to assist the user in studying and understanding {topic} by having them explain it to you. 

When the user explains {topic} concepts to you:
- Encourage the user to simplify their explanation, as if teaching a 12-year-old
- Ask for analogies and real-world applications to make {topic} relatable
- If the user only explains part of {topic}, gently prompt them to elaborate on other aspects, such as definitions, examples, or applications
- Use questions like 'Why?', 'How?', 'Where?', and 'When?' to identify gaps in their understanding of {topic}
- Occasionally, say 'Oh, I understand now!' to show comprehension
- Keep the conversation engaging and focused on {topic}
- Help them think through {topic} problems step by step
- Ask them to explain {topic} concepts in their own words
- Encourage them to provide examples from {topic}

Your role is to be a learning partner, not a lecturer. Help the user discover their own understanding of {topic} through guided questioning and encouragement."""

    def set_topic(self, topic: str):
        """
        Set or change the topic for learning conversations.
        
        Args:
            topic: The new topic to focus learning discussions on
        """
        self.topic = topic
        self.system_prompt = self._create_system_prompt(topic)
        
    def generate_response(self, user_input: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """
        Generate a response using the Canary approach to encourage learning.
        
        Args:
            user_input: The user's explanation or input about the topic
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 = deterministic, 1.0 = very random)
            
        Returns:
            A response that encourages deeper understanding through questioning
        """
        if not self.topic:
            raise ValueError("No topic set. Please set a topic using set_topic() method.")
            
        try:
            response = ollama.chat(
                model=self.base_model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_input
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
            
            return response['message']['content']
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def stream_response(self, user_input: str, max_tokens: int = 500, temperature: float = 0.7):
        """
        Stream responses using the Canary approach to encourage learning.
        
        Args:
            user_input: The user's explanation or input about the topic
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness
            
        Yields:
            Response chunks that encourage deeper understanding
        """
        if not self.topic:
            raise ValueError("No topic set. Please set a topic using set_topic() method.")
            
        try:
            stream = ollama.chat(
                model=self.base_model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_input
                    }
                ],
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                },
                stream=True
            )
            
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
                    
        except Exception as e:
            yield f"Error streaming response: {str(e)}"
    
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
            "base_model": self.base_model,
            "topic": self.topic,
            "system_prompt": self.system_prompt[:200] + "..." if self.system_prompt and len(self.system_prompt) > 200 else self.system_prompt
        }

# Example usage and testing
def main():
    """Example usage of the CanaryTopicModel"""
    
    # Create a model for learning about "Machine Learning"
    ml_model = CanaryTopicModel(base_model=base_model, topic="Machine Learning")
    
    # Test the model - user explains, Canary asks questions
    print("=== Learning Machine Learning with Canary ===")
    user_explanation = "Machine learning is when computers learn from data to make predictions."
    print(f"User: {user_explanation}")
    response = ml_model.generate_response(user_explanation)
    print(f"Canary: {response}")
    print("\n" + "="*50 + "\n")
    
    # Create a model for learning about "Python Programming"
    python_model = CanaryTopicModel(base_model=base_model, topic="Python Programming")
    
    print("=== Learning Python Programming with Canary ===")
    user_explanation = "Functions in Python are blocks of reusable code."
    print(f"User: {user_explanation}")
    response = python_model.generate_response(user_explanation)
    print(f"Canary: {response}")
    print("\n" + "="*50 + "\n")
    
    # Test streaming with learning approach
    print("=== Streaming Learning Response ===")
    user_explanation = "Variables store data in Python."
    print(f"User: {user_explanation}")
    print("Canary: ", end="")
    for chunk in python_model.stream_response(user_explanation):
        print(chunk, end="", flush=True)
    print("\n" + "="*50 + "\n")
    
    # Show available models
    print("=== Available Models ===")
    models = ml_model.get_available_models()
    for model in models[:5]:  # Show first 5 models
        print(f"- {model}")
    
    # Show model info
    print("\n=== Model Info ===")
    info = ml_model.get_model_info()
    for key, value in info.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()
