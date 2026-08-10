import sys
import json
from app import app

sentences = {
    "NON-1": "I had a wonderful day today walking in the park and spending time with my family.",
    "NON-2": "Everything is going well with my new job and I feel happy and accomplished.",
    "NON-3": "I enjoyed cooking dinner tonight and I am looking forward to the weekend.",
    "DEP-1": "I feel completely hopeless, empty inside, and I can't find any reason to keep going.",
    "DEP-2": "Everything feels dark and exhausting, I just want to lie in bed and disappear.",
    "DEP-3": "I am drowning in sadness every day and I don't think things will ever get better."
}

with app.app_context():
    client = app.test_client()
    for name, text in sentences.items():
        res = client.post('/predict', json={"journal": text})
        print(f"[{name}] {res.get_json()}")
