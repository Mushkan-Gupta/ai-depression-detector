import sys
sys.stdout.reconfigure(encoding='utf-8')

MILD_NEGATIVE_KEYWORDS = [
    'sad', 'lonely', 'anxious', 'anxiety', 'stressed', 'stress', 'overwhelmed',
    'tired', 'exhausted', 'struggling', 'unmotivated', 'hard time', 'difficult',
    'worried', 'fear', 'insomnia', 'can\'t sleep', 'low energy', 'withdrawn',
    'down', 'crying', 'numb', 'flat', 'irritable', 'frustrated', 'burned out',
    'lost', 'confused', 'empty', 'grief', 'grieving', 'loss', 'heartbroken',
    'hopeless', 'worthless', 'give up', 'no point', 'no energy',
    'not okay', 'falling apart', 'running on empty', 'no motivation',
    'isolating', 'withdrawing', 'can\'t function',
]
POSITIVE_KEYWORDS = [
    'happy', 'happiness', 'grateful', 'gratitude', 'excited', 'joy', 'joyful',
    'peaceful', 'content', 'hopeful', 'motivated', 'thankful', 'loved', 'love',
    'optimistic', 'wonderful', 'great day', 'feeling good', 'blessed', 'proud',
    'energetic', 'rested', 'calm', 'connected', 'supported', 'inspired',
    'fulfilled', 'relieved', 'laughter', 'laugh', 'smile', 'smiling',
    'looking forward', 'positive', 'thriving', 'growing',
]

MIXED_1 = """It has been a rollercoaster of a month. Some days I feel almost like myself, I can get through 
my to-do list, laugh with my flatmate, feel engaged with work. Other days are really dark and 
I struggle to find any point to anything. I never know which version of me I will wake up as.

The good days feel great and I cling to them. But the bad days feel impossibly heavy. Yesterday 
I cried for an hour without knowing why. I sat on the bathroom floor and just let it all out. 
Afterward I felt a bit lighter but also embarrassed and unsure what triggered it.

My anxiety has been particularly bad this month. Crowds, loud environments, even phone calls make 
my heart race and my chest tighten. I have been avoiding situations that used to not bother me at 
all. It is limiting and frustrating.

I am not in crisis but I am struggling. I have good support around me, friends who check in and 
a sister who I can talk to honestly. That helps a lot. I just want the bad days to come less 
frequently. I want more stability and peace of mind."""

MIXED_3 = """I have been grieving the loss of my grandmother for the past two months. She was the most important 
person in my life and the world feels genuinely different without her in it. There is a specific 
kind of silence now where her voice used to be. I miss her every single day.

The grief comes in waves. Some days I am functional and I can even feel gratitude for the time 
we had. Other days I am devastated, I see something she would have loved, or I reach for my 
phone to call her before remembering. The shock of that still hurts even after all this time.

I have been sad and tired and a bit withdrawn. I know this is a normal part of grief but it 
does not make it easier to bear. I have also felt some guilt, wondering if I visited enough, 
if I said all the right things. Logically I know I did my best but emotionally it is harder.

I have not lost hope. I know grief changes shape over time. I have a wonderful support network 
and I have started speaking to a grief counsellor which is helping. I am taking it one day at 
a time and being gentle with myself."""

for name, text in [("MIXED-1", MIXED_1), ("MIXED-3", MIXED_3)]:
    lower = text.lower()
    mild = [kw for kw in MILD_NEGATIVE_KEYWORDS if kw in lower]
    pos  = [kw for kw in POSITIVE_KEYWORDS if kw in lower]
    neg_score = min(len(mild), 12) * 0.10 - len(pos) * 0.12
    print(f"\n{name}:")
    print(f"  mild hits ({len(mild)}): {mild}")
    print(f"  positive hits ({len(pos)}): {pos}")
    print(f"  neg_score = {neg_score:.3f}")
    print(f"  Threshold 0.30 = {'REACH' if neg_score >= 0.30 else 'MISS'}")
