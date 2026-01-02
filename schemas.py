"""Pydantic schemas for API validation."""
# These handle all request/response validation - Pydantic is awesome for this
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = None
    weight: Optional[int] = Field(None, ge=1, le=500)
    height: Optional[int] = Field(None, ge=1, le=300)
    medical_conditions: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    allergies: Optional[List[str]] = None


class UserResponse(UserBase):
    id: int
    age: Optional[int]
    gender: Optional[str]
    onboarding_completed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Message schemas
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    
    @validator('content')
    def validate_content(cls, v):
        # Prevent empty/whitespace-only messages
        if not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()


class MessageResponse(BaseModel):
    id: int
    user_id: int
    role: str
    content: str
    created_at: datetime
    message_metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
    has_more: bool
    next_cursor: Optional[int] = None


# Chat schemas
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class ChatResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    context_used: Optional[Dict[str, Any]] = None


# Memory schemas
class MemoryCreate(BaseModel):
    category: str
    key: str
    value: str
    importance: int = Field(default=1, ge=1, le=5)


class MemoryResponse(BaseModel):
    id: int
    category: str
    key: str
    value: str
    importance: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Protocol schemas
class ProtocolCreate(BaseModel):
    name: str
    category: str
    keywords: List[str]
    trigger_phrases: Optional[List[str]] = None
    description: Optional[str] = None
    response_template: str
    priority: int = Field(default=1, ge=1, le=10)
    requires_conditions: Optional[Dict[str, Any]] = None


class ProtocolResponse(BaseModel):
    id: int
    name: str
    category: str
    keywords: List[str]
    description: Optional[str]
    priority: int
    
    class Config:
        from_attributes = True


# Typing indicator schemas
class TypingUpdate(BaseModel):
    is_typing: bool


class TypingStatus(BaseModel):
    is_typing: bool
    updated_at: datetime


# Onboarding schemas
class OnboardingData(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = None
    weight: Optional[int] = Field(None, ge=1, le=500)
    height: Optional[int] = Field(None, ge=1, le=300)
    medical_conditions: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    allergies: Optional[List[str]] = []


# Health check
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    database: str
    redis: Optional[str] = None
