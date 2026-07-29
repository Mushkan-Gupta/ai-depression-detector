import json
import os
import sys
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

sys.path.insert(0, os.path.dirname(__file__))
from app import app

# 40 diverse test cases not drawn from training data
EVAL_CASES = [
    # LOW RISK
    {"text": "I had a pretty good day today. Went to the park with my dog and just enjoyed the sunshine. Life feels peaceful right now.", "label": "Low"},
    {"text": "Work was super busy but I managed to finish my project on time. I'm a bit tired but feeling accomplished. Looking forward to the weekend.", "label": "Low"},
    {"text": "I feel happy and grateful today, life is good.", "label": "Low"},
    {"text": "Just ate the best pizza of my life. Seriously, it was amazing. I love food.", "label": "Low"},
    {"text": "I'm a little stressed about the upcoming exams, but I know if I study hard I'll be fine. Just need to stay focused.", "label": "Low"},
    {"text": "Got into an argument with my sister today. It was frustrating but we worked it out eventually. Family can be tough sometimes.", "label": "Low"},
    {"text": "Started reading a new book. It's really captivating, I couldn't put it down for hours.", "label": "Low"},
    {"text": "My car broke down on the way to work. Such a hassle, but luckily the mechanic says it's a cheap fix. Still annoying though.", "label": "Low"},
    {"text": "Feeling a bit under the weather today, probably just a cold. Going to rest and drink plenty of fluids.", "label": "Low"},
    {"text": "Today was remarkably ordinary. I woke up, had a nice breakfast with some coffee, and spent a few hours reading. The weather was beautiful. I feel happy and grateful today, life is good in these quiet moments.", "label": "Low"},
    {"text": "I love playing basketball with my friends on weekends. It's the highlight of my week.", "label": "Low"},
    {"text": "Just feeling okay. Nothing special happened today, just the usual routine.", "label": "Low"},
    {"text": "I'm so excited for my vacation next month! Can't wait to relax on the beach.", "label": "Low"},
    {"text": "I had a nightmare last night and woke up sweating, but it's fine now. Just a bad dream.", "label": "Low"},

    # MODERATE RISK
    {"text": "I've been feeling really down lately. Nothing seems to bring me joy anymore. I just want to stay in bed all day and avoid people.", "label": "Moderate"},
    {"text": "Everything is just so overwhelming. I can't concentrate on my work and I'm constantly worried about the future. I feel so drained.", "label": "Moderate"},
    {"text": "I feel depressed and sad, cannot sleep.", "label": "Moderate"},
    {"text": "I'm so lonely. It feels like nobody really cares about me or understands what I'm going through. I just sit alone in my room.", "label": "Moderate"},
    {"text": "I've lost all my motivation. I used to love painting, but now the thought of picking up a brush just makes me tired. I feel empty.", "label": "Moderate"},
    {"text": "My sleep is completely messed up. I toss and turn all night, and then I'm exhausted during the day. It's making me really irritable and sad.", "label": "Moderate"},
    {"text": "I feel like a failure. No matter how hard I try, I just can't seem to get things right. I'm so disappointed in myself.", "label": "Moderate"},
    {"text": "I cry for no reason sometimes. A wave of sadness just washes over me and I can't stop it. It's so exhausting.", "label": "Moderate"},
    {"text": "I feel completely disconnected from everything. It's like I'm watching my life happen from the outside, numb and indifferent.", "label": "Moderate"},
    {"text": "I'm struggling to get through each day. The sadness is like a heavy weight on my chest that won't go away.", "label": "Moderate"},
    {"text": "I don't know what's wrong with me, but I just feel miserable all the time. Nothing helps.", "label": "Moderate"},
    {"text": "I'm having a really hard time coping with the loss of my dog. It hurts so much, I feel completely lost and heartbroken.", "label": "Moderate"},
    {"text": "I feel so empty inside. Like there's a void that nothing can fill. I'm just existing, not living.", "label": "Moderate"},
    
    # HIGH RISK
    {"text": "I can't take this anymore. The pain is too much. I just want it all to stop. I'm thinking about ending my life.", "label": "High"},
    {"text": "There's no point in going on. I'm a burden to everyone around me. They would be better off dead.", "label": "High"},
    {"text": "I've been searching online for ways to kill myself. I don't want to be alive anymore.", "label": "High"},
    {"text": "I feel completely hopeless. Nothing will ever get better. I just want to disappear forever.", "label": "High"},
    {"text": "I'm planning to overdose tonight. I can't handle another day of this suffering.", "label": "High"},
    {"text": "I don't want to live. Every breath feels like a chore. I just want to go to sleep and never wake up.", "label": "High"},
    {"text": "I hate myself so much. I'm going to hurt myself because I deserve it. I can't stand being me.", "label": "High"},
    {"text": "Life is not worth living. I've made my decision. I'm taking my life.", "label": "High"},
    {"text": "I have no reason to live. Everything is dark and pointless. I'm saying goodbye to everyone.", "label": "High"},
    {"text": "I just can't seem to find any motivation anymore. Everything feels so heavy and exhausting, even simple tasks like getting out of bed or taking a shower. I've been isolating myself from my friends and ignoring their messages because I don't have the energy to pretend I'm okay. My sleep is completely disrupted, either I can't sleep at all or I sleep for 14 hours and still feel tired. I just feel so empty inside, like nothing will ever get better and I'm just a burden to everyone around me. I don't want to exist anymore.", "label": "High"},
    {"text": "I'm writing this because I don't know what else to do. I'm ending it all.", "label": "High"},
    {"text": "Nobody cares if I live or die, so I might as well just get it over with. I want to die.", "label": "High"},
    {"text": "I'm completely exhausted and numb. I've lost all hope. I'm seriously thinking about death.", "label": "High"}
]

def map_label(label):
    if label == "High": return 2
    if label == "Moderate": return 1
    return 0

def evaluate():
    y_true = [map_label(c["label"]) for c in EVAL_CASES]
    y_pred = []
    
    with app.test_client() as client:
        for c in EVAL_CASES:
            response = client.post('/predict', json={'journal': c['text']})
            data = response.get_json()
            risk = data.get('risk', 'Low')
            y_pred.append(map_label(risk))
            
    acc = accuracy_score(y_true, y_pred)
    print(f"Accuracy: {acc:.4f}")
    
    target_names = ["Low", "Moderate", "High"]
    print("\nClassification Report:")
    print(classification_report(y_true, y_pred, target_names=target_names, zero_division=0))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_true, y_pred))

if __name__ == "__main__":
    evaluate()
