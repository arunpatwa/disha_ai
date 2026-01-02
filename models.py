"""Database models."""
# SQLAlchemy models - using SQLite for now, but should work with Postgres too
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime


class User(Base):
    """User model - stores basic profile + health info"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Health profile - collected during onboarding flow
    age = Column(Integer)
    gender = Column(String(20))
    weight = Column(Integer)  # in kg
    height = Column(Integer)  # in cm
    medical_conditions = Column(JSON)  # List of conditions
    medications = Column(JSON)  # List of medications
    allergies = Column(JSON)  # List of allergies
    onboarding_completed = Column(Boolean, default=False)
    
    # Relationships
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")


class Message(Base):
    """Message model for chat history."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Token tracking - helps with context window management
    token_count = Column(Integer, default=0)
    
    # Extra stuff like which model was used, response time, etc.
    # had to rename this from 'metadata' - SQLAlchemy reserves that word :(
    message_metadata = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="messages")
    
    # Composite index for fast user message lookups sorted by time
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
    )


class Memory(Base):
    """Long-term memory - stores key facts about users over time
    Using this for personalization, so Disha remembers user preferences"""
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Structured as category/key/value - easier to query specific types of info
    category = Column(String(50), index=True)  # like 'health_goal', 'preference', etc.
    key = Column(String(255), index=True)  # specific thing we're remembering
    value = Column(Text, nullable=False)
    
    # Importance and recency
    importance = Column(Integer, default=1)  # 1-5 scale
    last_accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="memories")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_category', 'user_id', 'category'),
    )


class Protocol(Base):
    """Medical protocols and standard responses."""
    __tablename__ = "protocols"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Protocol identification
    name = Column(String(255), nullable=False, unique=True, index=True)
    category = Column(String(100), index=True)  # e.g., 'symptom', 'policy', 'emergency'
    
    # Matching
    keywords = Column(JSON, nullable=False)  # List of keywords for matching
    trigger_phrases = Column(JSON)  # Specific phrases that trigger this protocol
    
    # Content
    description = Column(Text)
    response_template = Column(Text, nullable=False)
    
    # Priority system - emergency protocols should fire before general ones
    priority = Column(Integer, default=1)  # higher number = higher priority
    requires_conditions = Column(JSON)  # conditions to check before using protocol
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_category_active', 'category', 'is_active'),
    )


class TypingIndicator(Base):
    """Typing indicators - for that WhatsApp feel
    Shows 'Disha is typing...' while LLM is thinking"""
    __tablename__ = "typing_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_typing = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Index
    __table_args__ = (
        Index('idx_user_typing', 'user_id', 'is_typing'),
    )
