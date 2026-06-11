import requests, json

API = "http://127.0.0.1:5000"

MODERATE_TESTS = {
    "MOD-1": """Work has been really stressful lately. We are in the middle of a restructure and nobody seems 
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
of myself but I am not sure where to start.""",

    "MOD-2": """Lately I have been feeling really sad without knowing exactly why. Some days everything feels grey 
and heavy and I cannot shake it no matter what I do. I try to act normal around people but it takes 
a lot of effort to mask how I am really feeling inside.

My motivation has dropped significantly. Things I used to enjoy hold little interest for me. I start 
things and abandon them quickly. I find myself just staring at my phone without really taking anything in.

I have been eating irregularly and my sleep is disrupted. I either sleep too much or barely at all. 
My body feels heavy and sluggish most of the time.

I know I am probably dealing with some kind of depression. I have been here before and I recognise 
the signs. I am not at the point where I am completely unable to function, but I am tired and I 
want to feel like myself again. I am considering reaching out to a therapist.""",
}

# Check which HIGH keywords are being hit
HIGH_RISK_KEYWORDS = [
    'suicide', 'kill myself', 'end it all', 'want to die', 'better off dead',
    'no reason to live', 'self harm', 'hurt myself', 'ending my life',
    'taking my life', 'end my life', 'overdose on', 'not want to be alive',
    'wishing i was dead', 'thinking about death', 'no longer want to live',
]

for cid, text in MODERATE_TESTS.items():
    lower = text.lower()
    hits = [kw for kw in HIGH_RISK_KEYWORDS if kw in lower]
    print(f"\n{cid}: HIGH keyword hits: {hits if hits else 'NONE'}")
    
    resp = requests.post(f"{API}/predict", json={"journal": text}, timeout=10)
    d    = resp.json()
    print(f"  API result: risk={d.get('risk')}  confidence={d.get('confidence')}")
