"""Service layer for business logic."""
# Keeping all business logic separate from API routes - makes testing easier
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional, Dict, Any, Tuple
from models import User, Message, Memory, Protocol, TypingIndicator
from schemas import (
    UserCreate, MessageCreate, MemoryCreate, OnboardingData,
    MessageListResponse, MessageResponse
)
from llm_service import llm_service
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations."""
    
    @staticmethod
    def get_or_create_user(db: Session, username: str) -> User:
        """Get existing user or create new one - lazy user creation"""
        user = db.query(User).filter(User.username == username).first()
        if not user:
            # New user - create with default values
            user = User(username=username)
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user: {username}")
        return user
    
    @staticmethod
    def update_user_profile(db: Session, user_id: int, data: OnboardingData) -> User:
        """Update user profile after onboarding."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        user.age = data.age
        user.gender = data.gender
        user.weight = data.weight
        user.height = data.height
        user.medical_conditions = data.medical_conditions or []
        user.medications = data.medications or []
        user.allergies = data.allergies or []
        user.onboarding_completed = True
        
        db.commit()
        db.refresh(user)
        logger.info(f"Updated profile for user {user_id}")
        return user
    
    @staticmethod
    def get_user_profile(user: User) -> Dict[str, Any]:
        """Get user profile as dictionary."""
        return {
            "full_name": user.full_name,
            "age": user.age,
            "gender": user.gender,
            "weight": user.weight,
            "height": user.height,
            "medical_conditions": user.medical_conditions or [],
            "medications": user.medications or [],
            "allergies": user.allergies or []
        }


class MessageService:
    """Service for message operations."""
    
    @staticmethod
    def create_message(
        db: Session,
        user_id: int,
        role: str,
        content: str,
        token_count: int = 0,
        message_metadata: Optional[Dict] = None
    ) -> Message:
        """Save a message to DB - handles both user and assistant messages"""
        # Auto-count tokens if not provided
        if token_count == 0:
            token_count = llm_service.count_tokens(content)
        
        message = Message(
            user_id=user_id,
            role=role,
            content=content,
            token_count=token_count,
            message_metadata=message_metadata or {}
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    @staticmethod
    def get_messages(
        db: Session,
        user_id: int,
        limit: int = 50,
        before_id: Optional[int] = None
    ) -> MessageListResponse:
        """
        Cursor-based pagination - way better than offset/limit for infinite scroll
        Fetching newest first, then frontend reverses them for display
        """
        query = db.query(Message).filter(Message.user_id == user_id)
        
        if before_id:
            query = query.filter(Message.id < before_id)
        
        # Fetch one extra message to check if there's more (clever pagination trick)
        messages = query.order_by(desc(Message.created_at)).limit(limit + 1).all()
        
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]
        
        # Get total count
        total = db.query(Message).filter(Message.user_id == user_id).count()
        
        # Next cursor is the ID of the oldest message in this batch
        next_cursor = messages[-1].id if messages and has_more else None
        
        return MessageListResponse(
            messages=[MessageResponse.model_validate(msg) for msg in messages],
            total=total,
            has_more=has_more,
            next_cursor=next_cursor
        )
    
    @staticmethod
    def get_recent_messages(
        db: Session,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, str]]:
        """Get recent messages formatted for LLM context."""
        messages = (
            db.query(Message)
            .filter(Message.user_id == user_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
            .all()
        )
        
        # Reverse to chronological order
        messages = list(reversed(messages))
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]


class MemoryService:
    """Service for memory operations."""
    
    @staticmethod
    def create_memory(
        db: Session,
        user_id: int,
        category: str,
        key: str,
        value: str,
        importance: int = 1
    ) -> Memory:
        """Create or update a memory - deduplicates by category+key combo"""
        # Don't want duplicate memories - check if we already have this info
        existing = (
            db.query(Memory)
            .filter(
                and_(
                    Memory.user_id == user_id,
                    Memory.category == category,
                    Memory.key == key
                )
            )
            .first()
        )
        
        if existing:
            # Update existing memory instead of creating duplicate
            existing.value = value
            existing.importance = importance
            existing.last_accessed_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        
        memory = Memory(
            user_id=user_id,
            category=category,
            key=key,
            value=value,
            importance=importance
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return memory
    
    @staticmethod
    def get_relevant_memories(
        db: Session,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most relevant memories for context."""
        memories = (
            db.query(Memory)
            .filter(Memory.user_id == user_id)
            .order_by(
                desc(Memory.importance),
                desc(Memory.last_accessed_at)
            )
            .limit(limit)
            .all()
        )
        
        # Update last_accessed_at
        for memory in memories:
            memory.last_accessed_at = datetime.utcnow()
        db.commit()
        
        return [
            {
                "category": m.category,
                "key": m.key,
                "value": m.value,
                "importance": m.importance
            }
            for m in memories
        ]
    
    @staticmethod
    async def extract_and_store_memories(
        db: Session,
        user_id: int,
        conversation: str
    ):
        """Pull out important health info from conversation and save it
        LLM does the heavy lifting here - extracts key facts automatically"""
        try:
            memories = await llm_service.extract_memories(conversation)
            for mem_data in memories:
                MemoryService.create_memory(
                    db=db,
                    user_id=user_id,
                    category=mem_data.get("category", "general"),
                    key=mem_data.get("key", "info"),
                    value=mem_data.get("value", ""),
                    importance=mem_data.get("importance", 1)
                )
            logger.info(f"Extracted {len(memories)} memories for user {user_id}")
        except Exception as e:
            logger.error(f"Error extracting memories: {e}")


class ProtocolService:
    """Service for protocol operations."""
    
    @staticmethod
    def match_protocols(
        db: Session,
        user_message: str,
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Match relevant protocols based on user message."""
        # Get all active protocols
        protocols = (
            db.query(Protocol)
            .filter(Protocol.is_active == True)
            .order_by(desc(Protocol.priority))
            .all()
        )
        
        matched = []
        user_message_lower = user_message.lower()
        
        for protocol in protocols:
            # Check keywords
            keywords = protocol.keywords or []
            if any(keyword.lower() in user_message_lower for keyword in keywords):
                # Check trigger phrases
                trigger_phrases = protocol.trigger_phrases or []
                if trigger_phrases:
                    if any(phrase.lower() in user_message_lower for phrase in trigger_phrases):
                        matched.append({
                            "name": protocol.name,
                            "category": protocol.category,
                            "response_template": protocol.response_template,
                            "priority": protocol.priority
                        })
                else:
                    matched.append({
                        "name": protocol.name,
                        "category": protocol.category,
                        "response_template": protocol.response_template,
                        "priority": protocol.priority
                    })
        
        return matched[:3]  # Return top 3 matches
    
    @staticmethod
    def seed_default_protocols(db: Session):
        """Seed database with default medical protocols."""
        default_protocols = [
            {
                "name": "Fever Management",
                "category": "symptom",
                "keywords": ["fever", "temperature", "hot", "burning up"],
                "trigger_phrases": ["have fever", "running fever"],
                "description": "Protocol for managing fever symptoms",
                "response_template": """For fever management:
- If temp > 103°F (39.4°C) or fever lasts > 3 days, see a doctor immediately
- Stay hydrated, drink plenty of water
- Rest and avoid strenuous activity
- You can take paracetamol (per package instructions) if needed
- Monitor temperature regularly
- Seek immediate care if you have: severe headache, difficulty breathing, chest pain, or confusion""",
                "priority": 8
            },
            {
                "name": "Stomach Ache",
                "category": "symptom",
                "keywords": ["stomach", "tummy", "abdomen", "belly", "pain", "ache"],
                "trigger_phrases": ["stomach pain", "stomach ache", "tummy ache"],
                "description": "Protocol for stomach pain",
                "response_template": """For stomach discomfort:
- Eat light, bland foods (rice, banana, toast)
- Stay hydrated with water or ORS
- Avoid spicy, oily, or heavy foods
- Rest and don't eat for 2-3 hours if nauseous
- See a doctor if: severe pain, blood in stool, pain lasts > 2 days, or you have fever""",
                "priority": 7
            },
            {
                "name": "Headache",
                "category": "symptom",
                "keywords": ["headache", "head pain", "migraine"],
                "trigger_phrases": ["have a headache", "head is paining"],
                "description": "Protocol for headaches",
                "response_template": """For headache relief:
- Rest in a quiet, dark room
- Stay hydrated
- Apply cold/warm compress to forehead
- Can take paracetamol if needed
- Avoid screens and bright lights
- Seek immediate care if: sudden severe headache, with fever and stiff neck, after head injury, or with vision changes""",
                "priority": 6
            },
            {
                "name": "Emergency Symptoms",
                "category": "emergency",
                "keywords": ["chest pain", "difficulty breathing", "unconscious", "bleeding", "severe"],
                "trigger_phrases": ["can't breathe", "chest pain", "severe bleeding"],
                "description": "Emergency situation protocol",
                "response_template": """⚠️ This sounds like a medical emergency. Please seek immediate medical attention:
- Call emergency services (102/108) or go to nearest hospital
- Do NOT wait or try home remedies
- If chest pain: sit down, stay calm, take aspirin if available (unless allergic)
- If breathing difficulty: sit upright, stay calm, loosen tight clothing
- Have someone stay with you""",
                "priority": 10
            },
            {
                "name": "Refund Policy",
                "category": "policy",
                "keywords": ["refund", "money back", "cancel", "subscription"],
                "trigger_phrases": ["want refund", "cancel subscription"],
                "description": "Refund and cancellation policy",
                "response_template": """Our refund policy:
- You can cancel subscription anytime from settings
- Refunds available within 7 days of purchase
- Contact support@disha.health with your username
- Refunds processed within 5-7 business days
- For specific queries, I can connect you with our support team""",
                "priority": 5
            }
        ]
        
        # Insert protocols if they don't exist already
        for protocol_data in default_protocols:
            existing = db.query(Protocol).filter(
                Protocol.name == protocol_data["name"]
            ).first()
            
            if not existing:
                protocol = Protocol(**protocol_data)
                db.add(protocol)
        
        db.commit()
        logger.info("Seeded default protocols")
        # TODO: might want to add more protocols for chronic conditions


class ChatService:
    """Main service for chat operations."""
    
    @staticmethod
    async def process_message(
        db: Session,
        user: User,
        message_content: str
    ) -> Tuple[Message, Message]:
        """
        Process user message and generate AI response.
        Returns: (user_message, assistant_message)
        """
        # Create user message
        user_message = MessageService.create_message(
            db=db,
            user_id=user.id,
            role="user",
            content=message_content
        )
        
        # Check if onboarding needed
        is_onboarding = not user.onboarding_completed
        
        # Get user profile
        user_profile = UserService.get_user_profile(user)
        
        # Get relevant memories
        memories = MemoryService.get_relevant_memories(db, user.id)
        
        # Match relevant protocols
        protocols = ProtocolService.match_protocols(db, message_content, user_profile)
        
        # Create system prompt
        system_prompt = llm_service.create_system_prompt(
            user_profile=user_profile,
            memories=memories,
            protocols=protocols,
            is_onboarding=is_onboarding
        )
        
        # Get recent message history
        message_history = MessageService.get_recent_messages(db, user.id, limit=20)
        
        # Generate response
        response_content, metadata = await llm_service.generate_response(
            messages=message_history,
            system_prompt=system_prompt
        )
        
        # Add context info to metadata
        metadata["protocols_used"] = [p["name"] for p in protocols]
        metadata["memories_used"] = len(memories)
        metadata["is_onboarding"] = is_onboarding
        
        # Create assistant message
        assistant_message = MessageService.create_message(
            db=db,
            user_id=user.id,
            role="assistant",
            content=response_content,
            message_metadata=metadata
        )
        
        # Extract and store memories (async, don't wait)
        if len(message_history) % 5 == 0:  # Every 5 messages
            conversation = f"User: {message_content}\nAssistant: {response_content}"
            await MemoryService.extract_and_store_memories(
                db, user.id, conversation
            )
        
        return user_message, assistant_message


class TypingService:
    """Service for typing indicators."""
    
    @staticmethod
    def update_typing_status(db: Session, user_id: int, is_typing: bool):
        """Update typing indicator status."""
        indicator = db.query(TypingIndicator).filter(
            TypingIndicator.user_id == user_id
        ).first()
        
        if not indicator:
            indicator = TypingIndicator(user_id=user_id, is_typing=is_typing)
            db.add(indicator)
        else:
            indicator.is_typing = is_typing
            indicator.updated_at = datetime.utcnow()
        
        db.commit()
    
    @staticmethod
    def get_typing_status(db: Session, user_id: int) -> Dict:
        """Get typing status for assistant."""
        indicator = db.query(TypingIndicator).filter(
            TypingIndicator.user_id == user_id
        ).first()
        
        if indicator:
            return {
                "is_typing": indicator.is_typing,
                "updated_at": indicator.updated_at
            }
        return {"is_typing": False, "updated_at": None}
