"""Test script to verify the application is working."""
import requests
import json
import time

BASE_URL = "http://localhost:8000"
USERNAME = "test_user"

def test_health():
    """Test health check endpoint."""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    print(f"✓ Health check: {data['status']}")
    return data

def test_send_message(message):
    """Test sending a message."""
    print(f"\nSending message: {message}")
    response = requests.post(
        f"{BASE_URL}/api/chat?username={USERNAME}",
        json={"message": message}
    )
    assert response.status_code == 200
    data = response.json()
    print(f"✓ User: {data['user_message']['content']}")
    print(f"✓ Assistant: {data['assistant_message']['content']}")
    return data

def test_get_messages():
    """Test getting message history."""
    print("\nFetching message history...")
    response = requests.get(f"{BASE_URL}/api/messages?username={USERNAME}")
    assert response.status_code == 200
    data = response.json()
    print(f"✓ Total messages: {data['total']}")
    print(f"✓ Has more: {data['has_more']}")
    return data

def test_seed_protocols():
    """Test seeding protocols."""
    print("\nSeeding protocols...")
    response = requests.post(f"{BASE_URL}/api/protocols/seed")
    assert response.status_code == 200
    print("✓ Protocols seeded")
    return response.json()

def test_get_protocols():
    """Test getting protocols."""
    print("\nFetching protocols...")
    response = requests.get(f"{BASE_URL}/api/protocols")
    assert response.status_code == 200
    protocols = response.json()
    print(f"✓ Found {len(protocols)} protocols")
    for p in protocols[:3]:
        print(f"  - {p['name']} ({p['category']})")
    return protocols

def run_tests():
    """Run all tests."""
    print("=" * 60)
    print("Disha AI - Integration Tests")
    print("=" * 60)
    
    try:
        # Test health
        test_health()
        
        # Seed protocols
        test_seed_protocols()
        test_get_protocols()
        
        # Test conversation
        test_send_message("Hi! I'm feeling a bit under the weather today.")
        time.sleep(1)
        
        test_send_message("I have a slight headache and fever.")
        time.sleep(1)
        
        # Get message history
        test_get_messages()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to server. Is it running?")
        print("Run: python main.py")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")

if __name__ == "__main__":
    run_tests()
