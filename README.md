# Disha - AI Health Coach

India's first AI health coach with persistent memory and protocol-driven conversations.

**Live Demo**: [https://disha-ai-rg86.onrender.com](https://disha-ai-rg86.onrender.com/)

## Running Locally

### Prerequisites
- Python 3.8+
- OpenAI API Key or Anthropic API Key

### Setup Steps

```bash
# 1. Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Initialize database
python init_db.py  # Creates tables + seeds 5 medical protocols

# 4. Run server
python main.py  # http://localhost:8000
```

### Environment Variables

```env
OPENAI_API_KEY=sk-...           # Required: Your OpenAI API key
LLM_PROVIDER=openai             # Options: openai, anthropic, demo
DATABASE_URL=sqlite:///./disha_ai.db  # SQLite by default
```

## Architecture

### Backend Structure (Layered)

```
main.py          → API routes (FastAPI endpoints)
services.py      → Business logic (UserService, ChatService, MemoryService, etc.)
llm_service.py   → LLM abstraction (OpenAI/Anthropic/Demo)
models.py        → Database models (SQLAlchemy ORM)
database.py      → DB connection + session management
```

### Key Design Decisions

**1. Smart Context Management**
- Truncates conversation to fit 8K token limit
- Keeps recent messages + system prompt with user profile/memories/protocols
- Uses tiktoken for accurate token counting

**2. Long-Term Memory System**
- LLM extracts key health facts every 5 messages
- Stores as category/key/value with importance (1-5)
- Only high-importance memories (≥3) injected into context

**3. Medical Protocol System**
- Pre-defined protocols for common scenarios (fever, emergency, etc.)
- Keyword matching triggers protocol responses
- Ensures consistent, safe medical guidance

**4. Cursor-Based Pagination**
- Uses message IDs as cursors for infinite scroll
- More efficient than offset-based for large datasets

**5. Multi-Provider LLM**
- Abstraction supports OpenAI, Anthropic, Demo mode
- Easy switching via `LLM_PROVIDER` env var

## LLM Integration

### Provider: OpenAI GPT-4o-mini
- **Model**: `gpt-4o-mini`
- **Config**: max_tokens=1000, temperature=0.7
- **Why**: Fast, cost-effective, good for conversational AI

### Prompting Strategy

**Two-Stage Approach:**

1. **Onboarding Mode** (new users)
   - Warm, conversational tone
   - Naturally gathers: age, gender, weight, height, conditions, medications, allergies
   - One question at a time, non-interrogative

2. **Regular Mode** (after onboarding)
   - Injects user profile + relevant memories + matching protocols
   - Maintains context across conversations
   - WhatsApp-like brevity (2-3 sentences)

**System Prompt Structure:**
```
You are Disha, India's first AI health coach...

USER PROFILE:
- Age: 30, Gender: male, Weight: 75kg, Height: 180cm
- Conditions: asthma | Medications: albuterol | Allergies: peanuts

MEMORIES (top 5 by importance):
- User prefers morning workouts
- Had flu last month

ACTIVE PROTOCOLS (matched by keywords):
[Emergency Protocol]: If chest pain/breathing issues → call 102/108
[Fever Protocol]: Rest, hydration, paracetamol if needed
```

**Memory Extraction** (every 5 messages):
- LLM analyzes conversation for key health facts
- Returns JSON: `[{category, key, value, importance}]`
- Categories: health_goal, preference, medical_history, lifestyle

**Context Window Management:**
- Limit: 8000 tokens (context) + 1000 tokens (response)
- Strategy: Keep recent messages, drop older ones if needed
- Always preserve full system prompt with profile/memories/protocols

## Trade-offs & Future Improvements

### Key Trade-offs Made

| Decision | Why | Trade-off | Production Solution |
|----------|-----|-----------|---------------------|
| **SQLite** | No setup, easy local dev | Poor concurrent writes, no scalability | PostgreSQL with pgBouncer |
| **Username-based auth** | Focus on AI features first | Zero security | JWT + OAuth + rate limiting |
| **HTTP polling** | Simple, works everywhere | Not real-time, more API calls | WebSockets for live updates |
| **Keyword protocol matching** | Fast, predictable | Misses contextual triggers | Semantic search with embeddings |
| **Single LLM call/msg** | Simple, low cost | No multi-turn reasoning | Function calling + tool use |

### If I Had More Time...

**High Priority:**
- [ ] JWT authentication + rate limiting
- [ ] WebSocket real-time messaging
- [ ] PostgreSQL + Redis caching
- [ ] Function calling (book appointments, set reminders)
- [ ] Semantic memory search with embeddings
- [ ] Unit tests (80%+ coverage)

**Medical Features:**
- [ ] Symptom checker flow
- [ ] Medication reminders + tracking
- [ ] Lab report analysis (PDF upload)
- [ ] Multi-language support (Hindi, Tamil, etc.)

**Advanced:**
- [ ] Multi-modal (image support for symptoms)
- [ ] RAG with medical knowledge base
- [ ] Voice input/output
- [ ] HIPAA/GDPR compliance
- [ ] Mobile app (React Native)

**Time Spent:** ~10 hours (planning, backend, LLM integration, frontend, testing, docs)

---

Built for Curelink Backend Engineer Take-Home Assignment
