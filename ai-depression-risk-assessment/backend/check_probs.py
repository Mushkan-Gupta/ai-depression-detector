import pickle, numpy as np

with open('depression_model.pkl','rb') as f: model=pickle.load(f)
with open('vectorizer.pkl','rb') as f:  vec=pickle.load(f)

samples = [
    ('LOW-1',   'Low',      'I feel grateful content peaceful happy motivated wonderful excited hopeful thankful blessed great day'),
    ('LOW-2',   'Low',      'productive week great feedback friends dinner happy optimistic proud loved good'),
    ('MOD-1',   'Moderate', 'anxious stressed overwhelmed struggling tired exhausted cant sleep work hard difficult'),
    ('MOD-2',   'Moderate', 'sad lonely depressed unmotivated no energy exhausted struggling crying numb'),
    ('HIGH-1',  'High',     'hopeless worthless want to die no point give up feel completely hopeless'),
    ('HIGH-2',  'High',     'ending my life worthless hopeless cannot go on suicide thoughts'),
    ('MIXED-1', 'Moderate', 'anxious panic stress tired lonely overwhelmed some good days some very dark days'),
]

print("  ID           Expected     dep_prob   raw_pred")
print("  " + "-"*50)
for sid, exp, text in samples:
    v   = vec.transform([text])
    p   = model.predict_proba(v)[0]
    raw = model.predict(v)[0]
    print(f"  {sid:<13} {exp:<13} {p[1]:.4f}     {raw}")
