import requests
import json
import os

# Assuming app.py is running locally or we can just import and call predict.
# Since app.py requires Flask context, it's easier to simulate the logic or start a test client.
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app, keyword_classify

def test_predictions():
    cases = [
        {
            "name": "Case 1: Long calm positive",
            "text": "Today was a remarkably ordinary but pleasant day. I woke up, had a nice breakfast with some coffee, and spent a few hours reading a book by the window. The weather was beautiful, completely sunny with a gentle breeze. I feel happy and grateful today, life is good in these quiet moments. Later I might go for a walk and enjoy the outdoors. I'm looking forward to a relaxing evening.",
            "expected_risk": "Low"
        },
        {
            "name": "Case 2: Short positive",
            "text": "I feel happy and grateful today, life is good.",
            "expected_risk": "Low"
        },
        {
            "name": "Case 3: Long genuinely depressed",
            "text": "I just can't seem to find any motivation anymore. Everything feels so heavy and exhausting, even simple tasks like getting out of bed or taking a shower. I've been isolating myself from my friends and ignoring their messages because I don't have the energy to pretend I'm okay. My sleep is completely disrupted, either I can't sleep at all or I sleep for 14 hours and still feel tired. I just feel so empty inside, like nothing will ever get better and I'm just a burden to everyone around me.",
            "expected_risk": "High or Moderate"
        },
        {
            "name": "Case 4: Short depressed",
            "text": "I feel depressed and sad, cannot sleep.",
            "expected_risk": "High or Moderate"
        }
    ]
    
    with app.test_client() as client:
        print("="*60)
        print("      REGRESSION TEST: 4 KEY CASES")
        print("="*60)
        for c in cases:
            response = client.post('/predict', json={'journal': c['text']})
            data = response.get_json()
            print(f"\n{c['name']}")
            print(f"Text: '{c['text']}'")
            print(f"Expected: {c['expected_risk']}")
            print(f"Actual: {data}")
            
if __name__ == "__main__":
    test_predictions()
