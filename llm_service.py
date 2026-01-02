"""LLM service for handling AI interactions."""
# Abstraction layer for different LLM providers - makes it easy to switch
# Currently supporting OpenAI, Anthropic, and a demo mode for testing
import openai
import anthropic
from typing import List, Dict, Optional, Tuple
from config import settings
import tiktoken
import logging
import random

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with LLM APIs."""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.max_context_tokens = settings.MAX_CONTEXT_TOKENS
        self.max_response_tokens = settings.MAX_RESPONSE_TOKENS
        
        # Initialize the right client based on provider
        # TODO: add retry logic with exponential backoff
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in .env file")
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "gpt-4o-mini"
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        elif self.provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not set in .env file")
            self.client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                max_retries=2
            )
            self.model = "claude-3-5-sonnet-20241022"
            # Anthropic uses similar tokenization
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        elif self.provider == "demo":
            # Demo mode - no API calls
            logger.warning("Running in DEMO mode - using mock responses")
            self.client = None
            self.model = "demo-mock"
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}. Use 'openai', 'anthropic', or 'demo'")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken - need this to avoid hitting context limits"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}. Using estimate.")
            # Rough estimate: 1 token ≈ 4 characters
            return len(text) // 4
    
    def truncate_context(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Truncate message history to fit within token limits.
        Keeps system prompt and most recent messages.
        """
        if max_tokens is None:
            max_tokens = self.max_context_tokens
        
        system_tokens = self.count_tokens(system_prompt)
        available_tokens = max_tokens - system_tokens - self.max_response_tokens
        
        # Always keep the most recent message
        truncated = []
        current_tokens = 0
        
        # Iterate from most recent to oldest
        for message in reversed(messages):
            msg_tokens = self.count_tokens(message["content"])
            if current_tokens + msg_tokens <= available_tokens:
                truncated.insert(0, message)
                current_tokens += msg_tokens
            else:
                # Can't fit more messages
                break
        
        # If we couldn't fit any messages, include at least the last one (truncated)
        if not truncated and messages:
            last_msg = messages[-1].copy()
            max_content_tokens = available_tokens - 100  # Safety margin
            
            # Truncate content if needed
            content_tokens = self.count_tokens(last_msg["content"])
            if content_tokens > max_content_tokens:
                # Rough truncation by character count
                chars_per_token = len(last_msg["content"]) / content_tokens
                max_chars = int(max_content_tokens * chars_per_token)
                last_msg["content"] = last_msg["content"][:max_chars] + "..."
            
            truncated = [last_msg]
        
        return truncated
    
    def create_system_prompt(
        self,
        user_profile: Dict,
        memories: List[Dict],
        protocols: List[Dict],
        is_onboarding: bool = False
    ) -> str:
        """Create a comprehensive system prompt."""
        
        if is_onboarding:
            return """You are Disha, India's first AI health coach. You're having your first conversation with a new user.

Your goal is to:
1. Welcome them warmly and introduce yourself naturally (don't sound robotic)
2. Understand their health goals and current situation
3. Gather basic information: age, any medical conditions, current medications, allergies
4. Ask about their lifestyle: sleep, exercise, diet, stress levels
5. Be empathetic and conversational - you're building a relationship, not conducting an interrogation

Important:
- Ask ONE question at a time, keep it conversational
- Show genuine interest in their responses
- Be supportive and non-judgmental
- Remember everything they tell you for future conversations
- Sound like a caring friend, not a clinical chatbot
- Use simple language, avoid medical jargon unless necessary

Keep your responses concise and natural. Think WhatsApp chat, not medical consultation."""
        
        # Regular conversation prompt
        prompt_parts = [
            "You are Disha, India's first AI health coach. You communicate like a caring friend on WhatsApp.",
            "\nYour personality:",
            "- Warm, empathetic, and supportive",
            "- Use simple language, avoid medical jargon",
            "- Keep responses concise (2-3 sentences usually)",
            "- Be conversational, not robotic or clinical",
            "- Show you remember past conversations",
            "- Ask follow-up questions when appropriate"
        ]
        
        # Add user profile if available
        if user_profile:
            prompt_parts.append("\n\nUser Profile:")
            if user_profile.get("full_name"):
                prompt_parts.append(f"- Name: {user_profile['full_name']}")
            if user_profile.get("age"):
                prompt_parts.append(f"- Age: {user_profile['age']}")
            if user_profile.get("gender"):
                prompt_parts.append(f"- Gender: {user_profile['gender']}")
            if user_profile.get("medical_conditions"):
                prompt_parts.append(f"- Medical Conditions: {', '.join(user_profile['medical_conditions'])}")
            if user_profile.get("medications"):
                prompt_parts.append(f"- Medications: {', '.join(user_profile['medications'])}")
            if user_profile.get("allergies"):
                prompt_parts.append(f"- Allergies: {', '.join(user_profile['allergies'])}")
        
        # Add relevant memories
        if memories:
            prompt_parts.append("\n\nRelevant Context from Past Conversations:")
            for memory in memories[:5]:  # Top 5 only - don't want to bloat the prompt
                prompt_parts.append(f"- {memory['key']}: {memory['value']}")
        
        # Add relevant protocols
        if protocols:
            prompt_parts.append("\n\nRelevant Medical Protocols:")
            for protocol in protocols[:3]:  # Max 3 protocols to keep context manageable
                prompt_parts.append(f"\n{protocol['name']}:")
                prompt_parts.append(protocol['response_template'])
        
        prompt_parts.append("\n\nImportant Guidelines:")
        prompt_parts.append("- For medical emergencies, always advise immediate medical attention")
        prompt_parts.append("- You're a health coach, not a doctor - don't diagnose or prescribe")
        prompt_parts.append("- Use the protocols above when relevant")
        prompt_parts.append("- Be encouraging about healthy habits")
        prompt_parts.append("- Keep responses short and WhatsApp-friendly")
        
        return "\n".join(prompt_parts)
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str
    ) -> Tuple[str, Dict]:
        """Call the LLM API and get response
        Returns both the text and some metadata about the call
        """
        try:
            # Make sure we're not over token limit
            truncated_messages = self.truncate_context(messages, system_prompt)
            
            metadata = {
                "provider": self.provider,
                "model": self.model,
                "messages_used": len(truncated_messages),
                "total_messages": len(messages)
            }
            
            # Demo mode
            if self.provider == "demo":
                return self._generate_demo_response(truncated_messages, metadata)
            
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *truncated_messages
                    ],
                    max_tokens=self.max_response_tokens,
                    temperature=0.7
                )
                
                content = response.choices[0].message.content
                metadata["tokens_used"] = response.usage.total_tokens
                
            elif self.provider == "anthropic":
                # Anthropic is different - system prompt is separate param, not in messages
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_response_tokens,
                    system=system_prompt,
                    messages=truncated_messages,
                    temperature=0.7
                )
                
                content = response.content[0].text
                metadata["tokens_used"] = response.usage.input_tokens + response.usage.output_tokens
            
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            return content, metadata
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def _generate_demo_response(self, messages: List[Dict[str, str]], metadata: Dict) -> Tuple[str, Dict]:
        """Demo mode - pattern matching for testing without burning API credits
        Just matching keywords, nothing fancy"""
        if not messages:
            response = "Hi! I'm Disha, your AI health coach. 👋 How can I help you today?"
        else:
            last_message = messages[-1]["content"].lower()
            
            # Simple pattern matching - could make this smarter
            # maybe use regex or even a small classifier model?
            if any(word in last_message for word in ["fever", "temperature", "hot"]):
                response = "I'm sorry to hear you have a fever. For fever management:\n\n- If temp > 103°F or lasts > 3 days, see a doctor\n- Stay hydrated and rest\n- You can take paracetamol as directed\n- Monitor your temperature regularly\n\nHow long have you had this fever?"
            
            elif any(word in last_message for word in ["headache", "head pain", "migraine"]):
                response = "Headaches can be tough! Here's what might help:\n\n- Rest in a quiet, dark room\n- Stay hydrated - drink plenty of water\n- Apply a cold compress to your forehead\n- Avoid screens and bright lights\n\nIf it persists or gets worse, please see a doctor. Is there anything else bothering you?"
            
            elif any(word in last_message for word in ["stomach", "tummy", "abdomen"]):
                response = "For stomach discomfort, I'd recommend:\n\n- Eat light, bland foods like rice and bananas\n- Stay hydrated with water or ORS\n- Avoid spicy and oily foods\n- Rest for a bit\n\nIf pain is severe or persists, please consult a doctor. When did this start?"
            
            elif any(word in last_message for word in ["hi", "hello", "hey"]):
                response = "Hello! 👋 I'm Disha, your AI health coach. I'm here to help you with health questions and wellness guidance. How are you feeling today?"
            
            elif any(word in last_message for word in ["thank", "thanks"]):
                response = "You're welcome! I'm always here to help. Is there anything else you'd like to know about your health?"
            
            elif "?" in last_message:
                response = "That's a great question! While I'm running in demo mode right now, in the full version I'd provide personalized health guidance based on your profile and history. Would you like to tell me more about what's concerning you?"
            
            else:
                responses = [
                    "I understand. Can you tell me more about what you're experiencing?",
                    "Thanks for sharing that with me. How long has this been going on?",
                    "I see. Are there any other symptoms you're noticing?",
                    "Got it. On a scale of 1-10, how would you rate your discomfort?",
                    "That's helpful to know. Have you experienced anything like this before?",
                ]
                response = random.choice(responses)
        
        metadata["tokens_used"] = len(response) // 4  # Rough estimate
        metadata["demo_mode"] = True
        
        return response, metadata
    
    async def extract_memories(self, conversation: str) -> List[Dict[str, str]]:
        """Use LLM to pull out important facts from conversation
        This is kinda meta - using AI to decide what's worth remembering
        Probably could optimize this prompt more but it works decent enough
        """
        try:
            prompt = f"""Analyze this conversation and extract key information that should be remembered about the user.
Return a JSON list of memories in this format:
[{{"category": "health_goal", "key": "primary_goal", "value": "description", "importance": 1-5}}]

Categories: health_goal, preference, medical_history, lifestyle, concern

Conversation:
{conversation}

Extract only factual, important information. Return empty list if nothing significant."""

            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.3
                )
                result = response.choices[0].message.content
            else:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                result = response.content[0].text
            
            # Parse JSON response
            import json
            try:
                memories = json.loads(result)
                return memories if isinstance(memories, list) else []
            except json.JSONDecodeError:
                # Sometimes LLM returns non-JSON or adds extra text
                logger.warning("Failed to parse memories JSON")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting memories: {e}")
            return []


# Singleton instance
llm_service = LLMService()
