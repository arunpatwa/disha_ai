# Disha - AI Health Coach

India's first AI health coach with persistent memory and protocol-driven conversations.

## Quick Start

### 1. Prerequisites
- Python 3.8+
- OpenAI API Key (recommended) or Anthropic API Key

### 2. Installation

```bash
# Clone and navigate to project
cd disha_ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API key
nano .env  # or use your preferred editor
```

Required configuration in `.env`:
```env
# Database
DATABASE_URL=sqlite:///./disha_ai.db

# LLM Provider (openai, anthropic, or demo)
LLM_PROVIDER=openai

# API Keys (add at least one based on LLM_PROVIDER)
OPENAI_API_KEY=your-openai-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here

# Server
PORT=8000
```

### 4. Set Up Database

```bash
# Initialize database and seed default protocols
python init_db.py
```

This creates:
- SQLite database with 5 tables (users, messages, memories, protocols, typing_indicators)
- Seeds 5 default medical protocols (Emergency, Fever, Headache, Stomach Pain, Refund)

### 5. Run the Application

```bash
# Start the server
python main.py

# Server will run at http://localhost:8000
```

Open http://localhost:8000 in your browser to start chatting with Disha!

## Deployment (Get a Public URL!)

### Quick Deploy to Render (Free)

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to [render.com](https://render.com) and sign up
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Render auto-detects `render.yaml`
   - Add your `OPENAI_API_KEY` in environment variables
   - Click "Create Web Service"

3. **Your app will be live!** 🎉
   - URL: `https://disha-ai-XXXX.onrender.com`
   - Check [DEPLOYMENT.md](DEPLOYMENT.md) for full guide

**Other Options**: Railway, Fly.io, Heroku - see [DEPLOYMENT.md](DEPLOYMENT.md) for details

## Architecture Overview

### Backend Structure

The application follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────┐
│   main.py (API Routes/Endpoints)    │
├─────────────────────────────────────┤
│   services.py (Business Logic)      │
├─────────────────────────────────────┤
│   llm_service.py (LLM Abstraction)  │
├─────────────────────────────────────┤
│   models.py (Database Models)       │
├─────────────────────────────────────┤
│   database.py (DB Connection)       │
└─────────────────────────────────────┘
```

#### Layers

1. **API Layer** (`main.py`)
   - FastAPI routes and endpoint definitions
   - Request/response validation with Pydantic schemas
   - Dependency injection for database sessions

2. **Service Layer** (`services.py`)
   - Business logic for all features
   - Services: UserService, MessageService, MemoryService, ProtocolService, ChatService, TypingService
   - Orchestrates between API and data layers

3. **LLM Layer** (`llm_service.py`)
   - Multi-provider support (OpenAI, Anthropic, Demo mode)
   - Context window management with token counting
   - Smart message truncation to stay within limits
   - Memory extraction from conversations

4. **Data Layer** (`models.py` + `database.py`)
   - SQLAlchemy ORM models
   - Database session management
   - Schema definitions with proper indexes

5. **Validation Layer** (`schemas.py`)
   - Pydantic models for type safety
   - Request/response validation
   - Data serialization

### Key Design Decisions

#### 1. SQLite Instead of PostgreSQL
- **Why**: Easier local setup, no separate database server needed
- **Trade-off**: Less suitable for production scale, but perfect for demo/development

#### 2. Context Window Management
- Implements smart truncation to stay within LLM token limits
- Keeps recent messages + system prompt (with user profile, memories, protocols)
- Uses tiktoken for accurate token counting

#### 3. Long-Term Memory System
- Automatically extracts key health information every 5 messages
- Stores as structured key-value pairs with importance ratings
- Retrieved and injected into system prompt for context

#### 4. Protocol-Based Responses
- Pre-defined medical protocols for common scenarios
- Keyword matching triggers appropriate protocol responses
- Ensures consistent, safe medical guidance

#### 5. Cursor-Based Pagination
- Uses message IDs as cursors for infinite scroll
- More efficient than offset pagination for large datasets
- Prevents duplicate messages during real-time updates

#### 6. Multi-Provider LLM Support
- Abstract interface supports OpenAI, Anthropic, or Demo mode
- Easy to switch providers via environment variable
- Demo mode for testing without API costs

## LLM Configuration

### Providers

**Primary: OpenAI GPT-4o-mini**
- Fast, cost-effective, good for conversational AI
- Configuration: max_tokens=1000, temperature=0.7

**Alternative: Anthropic Claude 3.5 Sonnet**
- More nuanced medical reasoning
- Configuration: max_tokens=1000, temperature=0.7

**Fallback: Demo Mode**
- Pattern-matched responses for testing
- No API key required

### Prompting Strategy

#### Multi-Stage System Prompts

1. **Onboarding Stage** (when `onboarding_completed=False`)
```
You are Disha, India's first AI health coach. You're warm, empathetic...
The user is new. Naturally gather: name, age, gender, weight, height,
medical conditions, medications, allergies.
Don't interrogate - make it conversational...
```

2. **Regular Conversation** (after onboarding)
```
You are Disha, India's first AI health coach...

USER PROFILE:
- Name: John, Age: 30, Gender: male
- Weight: 75kg, Height: 180cm
- Medical Conditions: asthma
- Current Medications: albuterol
- Allergies: peanuts

RELEVANT MEMORIES:
- User prefers morning workouts
- Had flu last month
...

ACTIVE PROTOCOLS:
[Fever Management Protocol]
Keywords: fever, temperature, hot
Response: Ask duration, measure temperature...
...
```

#### Context Management
- **Token Limits**: 8000 tokens for context, 1000 for response
- **Truncation Strategy**: Keep most recent messages + full system prompt
- **Memory Integration**: Only inject relevant memories (importance ≥ 3)
- **Protocol Matching**: Include protocols matching message keywords

#### Memory Extraction
Every 5 messages, asks LLM to extract key information:
```
Extract health-related memories from conversation:
- Medical conditions mentioned
- Lifestyle preferences
- Symptoms reported
- Treatment responses
...
Return as JSON array with category, key, value, importance.
```

## API Endpoints

### Core Endpoints

- `POST /api/chat` - Send message, get AI response
- `GET /api/messages` - Get paginated message history
- `GET /api/users/me` - Get user profile
- `PUT /api/users/me/onboarding` - Complete onboarding
- `POST /api/typing` - Update typing indicator
- `GET /health` - Health check endpoint

Full API documentation available at http://localhost:8000/docs (when running)

## Testing

```bash
# Run integration tests
python test_api.py

# Manual testing with curl
curl -X POST "http://localhost:8000/api/chat?username=testuser" \
  -H "Content-Type: application/json" \
  -d '{"message": "I have a fever"}'
```

## Project Structure

```
disha_ai/
├── main.py              # FastAPI app and routes
├── services.py          # Business logic layer
├── llm_service.py       # LLM integration
├── models.py            # Database models
├── schemas.py           # Pydantic schemas
├── database.py          # DB connection
├── config.py            # Configuration
├── init_db.py           # Database initialization
├── test_api.py          # Integration tests
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create from .env.example)
├── .env.example         # Environment template
└── static/
    └── index.html       # WhatsApp-like chat UI
```

## Troubleshooting

### Database Issues
```bash
# Reset database
rm disha_ai.db
python init_db.py
```

### API Key Issues
- Verify your API key is correct in `.env`
- Check you have credits/quota remaining
- Use `LLM_PROVIDER=demo` for testing without API key

### Port Already in Use
```bash
# Change PORT in .env
PORT=8001

# Or kill existing process
lsof -ti:8000 | xargs kill -9
```

## Features

- ✅ Persistent conversation history
- ✅ Long-term memory extraction
- ✅ Medical protocol matching
- ✅ Natural onboarding flow
- ✅ WhatsApp-like UI with infinite scroll
- ✅ Typing indicators
- ✅ Multi-provider LLM support
- ✅ Context window management
- ✅ Cursor-based pagination

## Tech Stack

- **Backend**: FastAPI 0.115.0
- **Database**: SQLite with SQLAlchemy 2.0.36
- **LLM**: OpenAI GPT-4o-mini / Anthropic Claude 3.5 Sonnet
- **Validation**: Pydantic 2.10.3
- **Frontend**: Vanilla JavaScript + HTML/CSS

---

Built for Curelink Backend Engineer Take-Home Assignment
