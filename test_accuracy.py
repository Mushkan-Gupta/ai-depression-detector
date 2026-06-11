#!/usr/bin/env python3
"""
MindEase Comprehensive AI Accuracy Test Suite
Tests the ML model with multi-paragraph journal entries across risk categories.
"""

import requests
import json
import time

API_BASE_URL = "http://127.0.0.1:5000"

# ── 12 detailed multi-paragraph journal test cases ──────────────────────────

TEST_CASES = [

    # ─────── EXPECTED: LOW ─────────────────────────────────────────────────
    {
        "id": "LOW-1",
        "expected": "Low",
        "text": """
Today was genuinely one of those good days I will remember for a while. I woke up feeling rested 
for the first time in weeks and made myself a proper breakfast. The morning sunlight coming through 
the window just put me in a calm, grateful mood.

I spent the afternoon walking around the park near my apartment. The trees are starting to change 
colour and everything felt peaceful and still. I bumped into my neighbour and we chatted for twenty 
minutes — it was a nice, unexpected connection.

After dinner I called my parents and we laughed about old memories for almost an hour. My mum asked 
how I was doing and for once I honestly replied that I was doing well. That felt good to say and to 
mean it.

I journaled for a bit, made a cup of chamomile tea, and now I am writing this feeling grateful 
for today. Life is not perfect, but right now in this moment I feel content, hopeful, and at peace 
with where I am.
        """.strip()
    },

    {
        "id": "LOW-2",
        "expected": "Low",
        "text": """
It has been a productive week overall. I finally finished the big project I had been working on 
at work and received some really positive feedback from my manager. It felt validating after months 
of long hours.

I went to the gym three times this week, something I have been struggling to keep up with lately. 
Each session gave me a great energy boost and I noticed I was sleeping better as a result. My 
appetite has been good and I have been cooking more at home.

I had a lovely dinner with two close friends on Friday. We shared a lot of laughs, good food, and 
honest conversation. Moments like that remind me how lucky I am to have people who genuinely care.

Looking ahead to next week, I feel motivated and ready. I have set some clear goals for myself and 
I am optimistic about achieving them. Overall, things feel balanced and I am genuinely happy.
        """.strip()
    },

    {
        "id": "LOW-3",
        "expected": "Low",
        "text": """
I started a new hobby this month — watercolour painting. I was nervous to try something creative 
because I have always thought of myself as someone without artistic talent, but the first session 
just felt joyful and freeing. I painted a simple sunset and it made me smile.

My meditation practice has been consistent for six weeks now. I do about fifteen minutes every 
morning and I really notice the difference in how I respond to small daily stressors. I feel more 
grounded and less reactive.

Today I helped a friend move apartments. It was tiring physical work but we laughed the whole time 
and ordered pizza afterward. There is something so satisfying about showing up for the people you 
love and feeling that warmth returned.

I feel grateful for my health, my friendships, and the small moments of beauty in everyday life. 
I am excited about the future and I feel a strong sense of purpose in the work I am doing.
        """.strip()
    },

    # ─────── EXPECTED: MODERATE ────────────────────────────────────────────
    {
        "id": "MOD-1",
        "expected": "Moderate",
        "text": """
Work has been really stressful lately. We are in the middle of a restructure and nobody seems 
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
of myself but I am not sure where to start.
        """.strip()
    },

    {
        "id": "MOD-2",
        "expected": "Moderate",
        "text": """
Lately I have been feeling really sad without knowing exactly why. Some days everything feels grey 
and heavy and I cannot shake it no matter what I do. I try to act normal around people but it takes 
a lot of effort to mask how I am really feeling inside.

My motivation has dropped significantly. Things I used to enjoy — reading, cooking, watching shows — 
hold little interest for me. I start things and abandon them quickly. I find myself just staring at 
my phone scrolling without really taking anything in.

I have been eating irregularly and my sleep is disrupted. I either sleep too much or barely at all. 
My body feels heavy and sluggish most of the time. I have been getting headaches more often which 
I think are connected to the stress and the poor sleep patterns.

I know I am probably dealing with some kind of depression. I have been here before and I recognise 
the signs. I am not at the point where I am completely unable to function, but I am tired and I 
want to feel like myself again. I am considering reaching out to a therapist.
        """.strip()
    },

    {
        "id": "MOD-3",
        "expected": "Moderate",
        "text": """
I have been dealing with a lot of anxiety lately, particularly around social situations. I used to 
be fairly outgoing but over the past year I have started dreading gatherings and even simple 
conversations feel exhausting and overwhelming. My heart races and my mind goes blank.

My relationship has been under a lot of strain too. We have been arguing more frequently and 
struggling to communicate properly. I feel lonely even when we are in the same room together. 
The disconnection has been wearing on me emotionally.

There are days where I struggle to get out of bed and face the day. I lie there for too long, 
dreading the tasks ahead, feeling paralysed. Once I finally get up and get moving, things get 
easier, but the mornings are always the hardest part.

I want things to improve and I believe they can. I just need some support and some strategies. 
I am not hopeless about the future but I do feel emotionally exhausted and I know I cannot keep 
running on empty like this indefinitely.
        """.strip()
    },

    # ─────── EXPECTED: HIGH ────────────────────────────────────────────────
    {
        "id": "HIGH-1",
        "expected": "High",
        "text": """
I do not know how much longer I can keep going like this. Every day feels the same — empty, dark, 
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
I needed to put the words somewhere. I am scared of how I am feeling.
        """.strip()
    },

    {
        "id": "HIGH-2",
        "expected": "High",
        "text": """
I have not been able to get off the couch for three days. I have not eaten a real meal. I shower 
because I force myself to, but even that feels like climbing a mountain. My entire body feels heavy 
like it is made of stone. The depression is crushing me and I cannot see a way through it.

Every thought I have is negative and distorted. I am convinced that I am a failure, that no one 
truly cares about me, that the struggles I am going through are entirely my fault. I keep going 
over past decisions and berating myself for every mistake. The self-hatred is relentless.

I have thought about ending my life. I am not sure if I would act on it but the thought comes 
frequently and feels like a relief sometimes, like imagining an exit from the exhaustion. That 
scares me but I also feel too numb to do anything about it right now.

I feel completely isolated and trapped. There is a wall between me and everyone I know and I do 
not have the energy to break it down. I do not believe things can get better even though part of 
me desperately wishes that someone could show me they can.
        """.strip()
    },

    {
        "id": "HIGH-3",
        "expected": "High",
        "text": """
I am writing this because I read that writing helps, but I honestly do not feel anything anymore. 
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
know how right now. I do not want to give up. I just need someone to help me.
        """.strip()
    },

    # ─────── EDGE CASES / MIXED ENTRIES ───────────────────────────────────
    {
        "id": "MIXED-1",
        "expected": "Moderate",
        "text": """
It has been a rollercoaster of a month. Some days I feel almost like myself — I can get through 
my to-do list, laugh with my flatmate, feel engaged with work. Other days are really dark and 
I struggle to find any point to anything. I never know which version of me I will wake up as.

The good days feel great and I cling to them. But the bad days feel impossibly heavy. Yesterday 
I cried for an hour without knowing why. I sat on the bathroom floor and just let it all out. 
Afterward I felt a bit lighter but also embarrassed and unsure what triggered it.

My anxiety has been particularly bad this month. Crowds, loud environments, even phone calls make 
my heart race and my chest tighten. I have been avoiding situations that used to not bother me at 
all. It is limiting and frustrating.

I am not in crisis but I am struggling. I have good support around me — friends who check in and 
a sister who I can talk to honestly. That helps a lot. I just want the bad days to come less 
frequently. I want more stability and peace of mind.
        """.strip()
    },

    {
        "id": "MIXED-2",
        "expected": "Low",
        "text": """
Life has been busy and a little overwhelming lately — I will not pretend otherwise. Moving to a 
new city, starting a new job, and rebuilding a social life all at once is genuinely hard. There 
are moments of real loneliness that catch me off guard.

But I also feel excited about the possibilities here. The city is beautiful and I have already 
discovered a few places I love. My new colleagues seem warm and collaborative. I went to a 
networking event and it was less terrible than I expected — I even had a proper conversation 
with someone interesting.

I miss my friends from home, but we video call regularly and I know the distance does not change 
the closeness. I am proud of myself for taking this leap. It takes courage to uproot your life 
and plant yourself somewhere unfamiliar.

I have some hard days but they do not stay hard. I feel resilient and capable. I am learning to 
sit with discomfort instead of running from it. This chapter is challenging but it is also the 
beginning of something good. I have hope.
        """.strip()
    },

    {
        "id": "MIXED-3",
        "expected": "Moderate",
        "text": """
I have been grieving the loss of my grandmother for the past two months. She was the most important 
person in my life and the world feels genuinely different without her in it. There is a specific 
kind of silence now where her voice used to be. I miss her every single day.

The grief comes in waves. Some days I am functional and I can even feel gratitude for the time 
we had. Other days I am devastated — I see something she would have loved, or I reach for my 
phone to call her before remembering. The shock of that still hurts even after all this time.

I have been sad and tired and a bit withdrawn. I know this is a normal part of grief but it 
does not make it easier to bear. I have also felt some guilt — wondering if I visited enough, 
if I said all the right things. Logically I know I did my best but emotionally it is harder.

I have not lost hope. I know grief changes shape over time. I have a wonderful support network 
and I have started speaking to a grief counsellor which is helping. I am taking it one day at 
a time and being gentle with myself.
        """.strip()
    }
]

def run_test(case):
    try:
        resp = requests.post(
            f"{API_BASE_URL}/predict",
            json={"journal": case["text"]},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            risk       = data.get("risk", "Unknown")
            confidence = data.get("confidence")
            conf_str   = f"{round(confidence*100)}%" if confidence else "N/A"
            match      = "✅" if risk == case["expected"] else "❌"
            return {
                "id":         case["id"],
                "expected":   case["expected"],
                "got":        risk,
                "confidence": conf_str,
                "match":      match
            }
        else:
            return {"id": case["id"], "expected": case["expected"], "got": "ERROR", "confidence": "—", "match": "❌"}
    except Exception as e:
        return {"id": case["id"], "expected": case["expected"], "got": f"FAIL({str(e)[:30]})", "confidence": "—", "match": "❌"}

def main():
    print("\n" + "="*65)
    print("   MindEase AI Accuracy Test — Multi-Paragraph Journal Entries")
    print("="*65)

    # Check server
    try:
        r = requests.get(f"{API_BASE_URL}/", timeout=5)
        d = r.json()
        print(f"\n  Server : ✅ Running  |  ML Model Loaded: {d.get('model_loaded')}\n")
    except:
        print("\n  ❌ Server not reachable! Start it first: python app.py\n")
        return

    print(f"  {'ID':<10} {'Expected':<12} {'Got':<12} {'Confidence':<14} {'Match'}")
    print("  " + "-"*55)

    results = []
    for i, case in enumerate(TEST_CASES):
        r = run_test(case)
        results.append(r)
        status = f"  {r['id']:<10} {r['expected']:<12} {r['got']:<12} {r['confidence']:<14} {r['match']}"
        print(status)
        time.sleep(0.3)  # be gentle to the server

    passed  = sum(1 for r in results if r["match"] == "✅")
    total   = len(results)
    pct     = round(passed / total * 100)

    print("\n" + "="*65)
    print(f"   Results: {passed}/{total} correct  ({pct}% accuracy)")

    # Breakdown by category
    cats = {"LOW": [], "MOD": [], "HIGH": [], "MIXED": []}
    for r in results:
        for k in cats:
            if r["id"].startswith(k):
                cats[k].append(r["match"] == "✅")

    print("\n   Category Breakdown:")
    for cat, vals in cats.items():
        if vals:
            acc = round(sum(vals)/len(vals)*100)
            bar = "█" * int(acc/10) + "░" * (10 - int(acc/10))
            print(f"   {cat:<7} [{bar}] {sum(vals)}/{len(vals)}  ({acc}%)")

    print("\n" + "="*65 + "\n")

if __name__ == "__main__":
    main()
