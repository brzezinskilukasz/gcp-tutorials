# post_random_names.py
import os
import random
import requests
import time

# Random names list
NAMES = [
    'Alice', 'Bob', 'Diana', 'Eve', 'Grace', 'Henry',
    'Ivy', 'Jack', 'Liam', 'Noah', 'Olivia', 'Paul',
    'Quinn', 'Ruby', 'Tina', 'Uma', 'Victor', 'Xander',
    'Yara', 'Zoe', 'Sarah', 'Mike', 'John', 'Lisa'
]

FRONTEND_URL = os.getenv("FRONTEND_URL")  # Your Cloud Run frontend URL

def post_random_name():
    name = random.choice(NAMES)
    
    # POST form data (not JSON) to match your /play endpoint
    response = requests.post(
        f"{FRONTEND_URL}/play",
        data={'name': name},  # Form data, not JSON
        allow_redirects=False  # Don't follow redirect to avoid getting HTML back
    )
    
    if response.status_code in [302, 200]:  # 302 = redirect (success)
        print(f"✅ Posted name: {name}")
    else:
        print(f"❌ Failed to post {name}: {response.status_code}")

def spam_names(count=10, delay=1):
    """Post multiple random names with delay"""
    for i in range(count):
        post_random_name()
        time.sleep(delay)
        
if __name__ == "__main__":
    spam_names(count=50, delay=2)  # Post 50 names, 2 seconds apart