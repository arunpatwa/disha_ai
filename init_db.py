"""Initialize database script."""
# Simple setup script - run this once to create tables and seed protocols
from database import engine, Base, SessionLocal
from models import User, Message, Memory, Protocol, TypingIndicator
from services import ProtocolService
import sys

def init_db():
    """Setup database - creates tables and adds default protocols"""
    try:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created successfully")
        
        # Add the default medical protocols
        print("\nSeeding default protocols...")
        db = SessionLocal()
        try:
            ProtocolService.seed_default_protocols(db)
            print("✓ Protocols seeded successfully")
        finally:
            db.close()
        
        print("\n✓ Database initialized successfully!")
        print("\nNext steps:")
        print("1. Update .env with your API keys")
        print("2. Run: python main.py")
        print("3. Open http://localhost:8000 in your browser")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error initializing database: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(init_db())
