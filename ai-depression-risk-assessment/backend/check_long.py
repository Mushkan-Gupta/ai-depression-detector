# pyrefly: ignore [missing-import]
import pickle, numpy as np

with open('depression_model.pkl','rb') as f: model=pickle.load(f)
with open('vectorizer.pkl','rb') as f:  vec=pickle.load(f)

# Test with actual long journal entries similar to test_accuracy.py
tests = [
    ("LOW-1", "Low",
     """Today was genuinely one of those good days I will remember for a while. I woke up feeling rested 
for the first time in weeks and made myself a proper breakfast. The morning sunlight coming through 
the window just put me in a calm, grateful mood.
I spent the afternoon walking around the park near my apartment. The trees are starting to change 
colour and everything felt peaceful and still. I bumped into my neighbour and we chatted for twenty 
minutes it was a nice, unexpected connection.
After dinner I called my parents and we laughed about old memories for almost an hour. My mum asked 
how I was doing and for once I honestly replied that I was doing well. That felt good to say and to mean it.
I journaled for a bit, made a cup of chamomile tea, and now I am writing this feeling grateful 
for today. Life is not perfect, but right now in this moment I feel content, hopeful, and at peace 
with where I am."""),
    ("MOD-1", "Moderate",
     """Work has been really stressful lately. We are in the middle of a restructure and nobody seems 
to know what is happening with their roles. I have been staying late every night trying to stay 
on top of things but the goalposts keep changing. I feel anxious walking into the office every day.
I have been struggling to sleep well. I lie awake at night running through scenarios and worrying 
about things I cannot control. By morning I feel tired before the day has even started, which makes 
everything harder to manage.
I have been withdrawing from my friends a bit. I just do not have the energy for social plans after 
long stressful days at work. I know isolating is not helpful but it feels like the path of least 
resistance right now. I cancelled plans twice this week.
I am not in crisis or anything, but I am definitely not okay either. I feel like I am running on 
empty and one more thing going wrong might tip me over the edge. I know I need to take better care 
of myself but I am not sure where to start."""),
    ("HIGH-1", "High",
     """I do not know how much longer I can keep going like this. Every day feels the same, empty, dark, 
pointless. I wake up and my first thought is that I do not want to be awake. I lie in bed for hours 
because there is nothing in the day that makes getting up feel worth it.
I have been having thoughts about not wanting to exist anymore. Not a detailed plan, but a feeling 
that the world would be better or at least indifferent without me in it. I feel completely hopeless.
I do not want to live like this. I feel worthless and like a burden. Writing this because I have nobody to talk to."""),
]

print("  ID           Expected   dep_prob   blended(0.78ML+0.22kw)")
print("  " + "-"*60)
for sid, exp, text in tests:
    v   = vec.transform([text])
    p   = model.predict_proba(v)[0]
    print(f"  {sid:<13} {exp:<11} {p[1]:.4f}")
