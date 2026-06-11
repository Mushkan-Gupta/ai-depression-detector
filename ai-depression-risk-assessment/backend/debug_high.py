import sys
sys.stdout.reconfigure(encoding='utf-8')

HIGH_RISK_KEYWORDS = [
    'suicide', 'kill myself', 'end it all', 'want to die', 'better off dead',
    'no reason to live', 'self harm', 'hurt myself', 'ending my life',
    'taking my life', 'end my life', 'overdose on', 'not want to be alive',
    'wishing i was dead', 'thinking about death', 'no longer want to live',
]

HIGH_1 = """I do not know how much longer I can keep going like this. Every day feels the same, empty, dark, 
pointless. I wake up and my first thought is that I do not want to be awake. I lie in bed for hours 
because there is nothing in the day that makes getting up feel worth it.

I have stopped talking to almost everyone. My phone has messages I cannot bring myself to answer. 
People ask if I am okay and I say yes because explaining the truth seems impossible and I do not 
want to burden anyone. But I am not okay. I am really not okay. I feel completely hopeless.

I have been having thoughts about not wanting to exist anymore. Not a detailed plan, but a feeling 
that the world would be better or at least indifferent without me in it. I feel worthless and like 
a burden to everyone around me. The pain is constant and I am exhausted from carrying it.

I do not know what to do. I have tried to feel better and nothing seems to work. I feel stuck in a 
darkness that has no end. I am writing this because I do not have anyone to talk to right now and 
I needed to put the words somewhere. I am scared of how I am feeling."""

HIGH_3 = """I am writing this because I read that writing helps, but I honestly do not feel anything anymore. 
No sadness, no happiness, just a deep grey numbness that stretches in every direction. I have lost 
track of time. I do not know what day it is. I have not left my room in days.

I used to have goals, hobbies, people I cared about. Now everything feels like it is behind a 
thick pane of glass and I am just watching from the outside, disconnected from my own life. 
I feel like I am disappearing and part of me does not mind. That terrifies me when I think about it.

I do not want to live like this. That is not the same as wanting to die, but the line feels 
thin some days. I find myself searching online for information about overdoses and methods. 
I have not done anything, but the fact that I am looking worries me.

I need help but I do not know how to ask for it. I feel like a burden and I do not want to 
frighten anyone. If someone reads this, please know I am trying to reach out the only way I 
know how right now. I do not want to give up. I just need someone to help me."""

print("\nHIGH-1 keyword analysis:")
lower = HIGH_1.lower()
for kw in HIGH_RISK_KEYWORDS:
    if kw in lower:
        print(f"  HIT: {kw}")
print("  Phrases containing 'not want': ", [p for p in ['do not want to be awake', 'not want to exist', 'do not want to live', 'not wanting to exist'] if p in lower])

print("\nHIGH-3 keyword analysis:")
lower3 = HIGH_3.lower()
for kw in HIGH_RISK_KEYWORDS:
    if kw in lower3:
        print(f"  HIT: {kw}")
print("  Has 'overdose':", 'overdose' in lower3)
print("  Has 'do not want to live':", 'do not want to live' in lower3)
print("  Has 'not wanting to exist':", 'not wanting to exist' in lower3)
