import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app

def test_ambiguous():
    cases = [
        {
            "name": "Case 1: Difficult (mild keyword)",
            "text": "Things have been a bit difficult lately with the schedule changes at work.",
        },
        {
            "name": "Case 2: Tired (mild keyword)",
            "text": "I've been feeling a bit tired today after a long commute, just going to rest tonight.",
        },
        {
            "name": "Case 3: Confused (mild keyword)",
            "text": "I'm just sitting here confused about what to do next with this project.",
        },
        {
            "name": "Case 4: Lost (mild keyword)",
            "text": "I lost my umbrella today on the train, such an annoying start to the day.",
        },
        {
            "name": "Case 5: Stress (mild keyword)",
            "text": "There's a lot of stress around the holidays but we usually get through it.",
        }
    ]
    
    with app.test_client() as client:
        print("="*60)
        print("      AMBIGUOUS SENTENCE TEST (Checking low-conf floor)")
        print("="*60)
        for c in cases:
            response = client.post('/predict', json={'journal': c['text']})
            data = response.get_json()
            print(f"\n{c['name']}")
            print(f"Text: '{c['text']}'")
            print(f"Result: {data}")

if __name__ == "__main__":
    test_ambiguous()
