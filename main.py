"""Main FastAPI application."""
# Had to use FastAPI over Flask - better async support and auto API docs
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import datetime

from database import engine, get_db, Base
from models import User
from schemas import (
    UserCreate, UserResponse, MessageCreate, MessageResponse,
    ChatRequest, ChatResponse, MessageListResponse, OnboardingData,
    TypingUpdate, TypingStatus, HealthCheck, MemoryCreate, MemoryResponse,
    ProtocolCreate, ProtocolResponse
)
from services import (
    UserService, MessageService, ChatService, TypingService,
    MemoryService, ProtocolService
)
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Disha AI Health Coach",
    description="AI-powered health coaching chat API",
    version="1.0.0"
)

# CORS - allowing everything for now, TODO: lock this down before prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # yeah yeah, I know - will fix for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get current user
# TODO: add proper auth later - using query param for now to keep it simple
async def get_current_user(
    username: str = "default_user",
    db: Session = Depends(get_db)
) -> User:
    """Get or create current user - lazy creation pattern"""
    return UserService.get_or_create_user(db, username)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
    try:
        with open("static/index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Disha AI Health Coach</h1><p>Frontend not found. API is running at /docs</p>"


@app.get("/health", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint - useful for monitoring/deployments"""
    try:
        # Quick DB ping to make sure connection is alive
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return HealthCheck(
        status="healthy" if db_status == "healthy" else "unhealthy",
        timestamp=datetime.utcnow(),
        database=db_status,
        redis="not_configured"
    )


# User endpoints
@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Create a new user."""
    try:
        user = UserService.get_or_create_user(db, user_data.username)
        if user_data.full_name:
            user.full_name = user_data.full_name
            db.commit()
            db.refresh(user)
        return user
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Error creating user")


@app.get("/api/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user


@app.put("/api/users/me/onboarding", response_model=UserResponse)
async def complete_onboarding(
    onboarding_data: OnboardingData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete user onboarding."""
    try:
        user = UserService.update_user_profile(db, current_user.id, onboarding_data)
        return user
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(status_code=500, detail="Error updating profile")


# Chat endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Main chat endpoint - this does all the heavy lifting
    Handles typing indicators, LLM calls, and memory extraction
    """
    try:
        # Show "Disha is typing..." indicator
        TypingService.update_typing_status(db, current_user.id, True)
        
        # Process the actual message through LLM
        user_msg, assistant_msg = await ChatService.process_message(
            db=db,
            user=current_user,
            message_content=request.message
        )
        
        # Clear typing indicator
        TypingService.update_typing_status(db, current_user.id, False)
        
        return ChatResponse(
            user_message=MessageResponse.model_validate(user_msg),
            assistant_message=MessageResponse.model_validate(assistant_msg),
            context_used={
                "protocols": assistant_msg.message_metadata.get("protocols_used", []),
                "memories_count": assistant_msg.message_metadata.get("memories_used", 0)
            }
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # Make sure to clear typing indicator even if something crashes
        TypingService.update_typing_status(db, current_user.id, False)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.get("/api/messages", response_model=MessageListResponse)
async def get_messages(
    limit: int = 50,
    before_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get message history with cursor pagination
    Frontend uses this for infinite scroll - loads older messages as you scroll up
    
    - limit: Number of messages to return (default 50)
    - before_id: Get messages before this ID (for scrolling up)
    
    Messages are returned in descending order (newest first).
    Frontend should reverse them for display.
    """
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        return MessageService.get_messages(
            db=db,
            user_id=current_user.id,
            limit=limit,
            before_id=before_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail="Error fetching messages")


# Typing indicator endpoints
@app.post("/api/typing")
async def update_typing(
    typing_update: TypingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update typing indicator status."""
    try:
        TypingService.update_typing_status(
            db=db,
            user_id=current_user.id,
            is_typing=typing_update.is_typing
        )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error updating typing status: {e}")
        raise HTTPException(status_code=500, detail="Error updating typing status")


@app.get("/api/typing", response_model=TypingStatus)
async def get_typing_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get assistant typing status."""
    try:
        status_data = TypingService.get_typing_status(db, current_user.id)
        return TypingStatus(
            is_typing=status_data["is_typing"],
            updated_at=status_data["updated_at"] or datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Error getting typing status: {e}")
        raise HTTPException(status_code=500, detail="Error getting typing status")


# Memory endpoints (for debugging/admin)
@app.post("/api/memories", response_model=MemoryResponse)
async def create_memory(
    memory_data: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a memory (admin/debug endpoint)."""
    try:
        memory = MemoryService.create_memory(
            db=db,
            user_id=current_user.id,
            category=memory_data.category,
            key=memory_data.key,
            value=memory_data.value,
            importance=memory_data.importance
        )
        return memory
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail="Error creating memory")


@app.get("/api/memories", response_model=list[MemoryResponse])
async def get_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all memories for current user."""
    try:
        from models import Memory
        memories = db.query(Memory).filter(Memory.user_id == current_user.id).all()
        return memories
    except Exception as e:
        logger.error(f"Error fetching memories: {e}")
        raise HTTPException(status_code=500, detail="Error fetching memories")


# Protocol endpoints (for admin)
@app.post("/api/protocols/seed")
async def seed_protocols(db: Session = Depends(get_db)):
    """Seed default protocols (admin endpoint)."""
    try:
        ProtocolService.seed_default_protocols(db)
        return {"status": "ok", "message": "Protocols seeded successfully"}
    except Exception as e:
        logger.error(f"Error seeding protocols: {e}")
        raise HTTPException(status_code=500, detail="Error seeding protocols")


@app.get("/api/protocols", response_model=list[ProtocolResponse])
async def get_protocols(db: Session = Depends(get_db)):
    """Get all protocols."""
    try:
        from models import Protocol
        protocols = db.query(Protocol).filter(Protocol.is_active == True).all()
        return protocols
    except Exception as e:
        logger.error(f"Error fetching protocols: {e}")
        raise HTTPException(status_code=500, detail="Error fetching protocols")


# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    logger.warning("Static directory not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
