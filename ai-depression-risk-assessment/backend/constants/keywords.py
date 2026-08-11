# ── Keyword Lexicons ───────────────────────────────────────────────────────

# HIGH severity: clear crisis / suicidality signals → always forces High
HIGH_RISK_KEYWORDS = [
    'suicide', 'kill myself', 'end it all', 'want to die', 'better off dead',
    'no reason to live', 'self harm', 'hurt myself', 'ending my life',
    'taking my life', 'end my life', 'overdose', 'not want to be alive',
    'wishing i was dead', 'thinking about death', 'no longer want to live',
    'not wanting to exist', 'do not want to live', 'do not want to exist',
    "don't want to live", "don't want to exist", 'want to disappear forever',
    'searching for methods', 'searching online for', 'looking up how to',
    'not worth living', 'life is not worth', 'no longer worth living',
]

# MODERATE severity: strong depression indicators but not crisis-level
MODERATE_RISK_KEYWORDS = [
    'depressed', 'depression', 'severely depressed', 'suicidal thoughts',
    'panic attack', 'no will to live', 'completely exhausted and numb',
    'numb inside', 'empty inside', 'hate myself', 'feel like a burden',
    'nobody cares', 'all alone', 'disconnected from', 'meaningless',
    "don't want to wake up", 'feel like disappearing', 'lost all hope',
    'no motivation whatsoever', 'crying all the time', 'deeply depressed',
]

# MILD signals: common stress/sadness words that need to accumulate to matter
MILD_NEGATIVE_KEYWORDS = [
    'sad', 'lonely', 'anxious', 'anxiety', 'stressed', 'stress', 'overwhelmed',
    'tired', 'exhausted', 'struggling', 'struggle', 'unmotivated', 'hard time', 'difficult',
    'worried', 'fear', 'insomnia', 'can\'t sleep', 'low energy', 'withdrawn',
    'down', 'crying', 'cried', 'numb', 'flat', 'irritable', 'frustrated',
    'burned out', 'burnt out', 'lost', 'confused', 'empty', 'grief', 'grieving',
    'loss', 'heartbroken', 'hopeless', 'give up', 'no point',
    'no energy', 'not okay', 'falling apart', 'running on empty', 'no motivation',
    'isolating', 'withdrawing', 'can\'t function', 'panic', 'dark days',
    'really dark', 'very dark', 'bad days', 'dark place', 'heavy mood',
    'miserable', 'dread', 'dreading', 'dreaded', 'guilt', 'guilty',
    'shame', 'ashamed', 'disconnected', 'detached', 'isolated', 'avoid',
    'feeling low', 'hard to function',
]

# POSITIVE signals: actively reduce depression probability
POSITIVE_KEYWORDS = [
    'happy', 'happiness', 'grateful', 'gratitude', 'excited', 'joy', 'joyful',
    'peaceful', 'content', 'hopeful', 'motivated', 'thankful', 'loved', 'love',
    'optimistic', 'wonderful', 'great day', 'feeling good', 'blessed', 'proud',
    'energetic', 'rested', 'calm', 'connected', 'supported', 'inspired',
    'fulfilled', 'relieved', 'laughter', 'laugh', 'smile', 'smiling',
    'looking forward', 'positive', 'thriving', 'growing',
]

# ── Indirect Ideation Phrases ──────────────────────────────────────────────
# These are well-known INDIRECT expressions of suicidal ideation or passive
# hopelessness. They do NOT use explicit crisis vocabulary, so they bypass the
# HIGH_RISK_KEYWORDS override — but they still carry serious clinical weight.
#
# Matching ANY of these phrases must guarantee AT MINIMUM Moderate risk,
# and they are logged/flagged so human reviewers can audit borderline cases.
# They must NEVER resolve to Low, regardless of the ML model's blended score.
#
# Do NOT weaken or remove this list — it is a safety feature.
INDIRECT_IDEATION_PHRASES = [
    # Exhaustion / giving up framing ("tired of fighting" is the exact failure case)
    "tired of fighting",
    "tired of trying",
    "tired of living like this",
    "exhausted from fighting",
    "can't keep fighting",
    "can't keep going",
    # "want to rest" cluster — very common indirect expression
    "want to rest now",
    "want to rest forever",
    "just want to rest",
    "need to rest permanently",
    "rest permanently",
    # Done / finished framing (context-checked: needs hopelessness/exhaustion co-signal)
    "i'm done",
    "im done",
    "i am done",
    "i'm done fighting",
    "im done fighting",
    # Can't continue
    "can't do this anymore",
    "cant do this anymore",
    "can't take this anymore",
    "cant take this anymore",
    "can't go on",
    "cant go on",
    "cannot go on",
    # Want it to stop
    "want it to stop",
    "want it all to stop",
    "want the pain to stop",
    "want everything to stop",
    # Don't want to be here
    "don't want to be here anymore",
    "dont want to be here anymore",
    "do not want to be here",
    "don't want to be here",
    # Better off without me
    "better off without me",
    "better off if i wasn't here",
    "better off if i was gone",
    "everyone would be better off",
    "world would be better without me",
    # Ready to go / leave
    "ready to go",
    "ready to leave",
    "ready for it to be over",
    # Disappear
    "want to disappear",
    "wish i could disappear",
    "wish i could just disappear",
    "just want to disappear",
    "want to just disappear",
    # Sleep / not wake up — well-known indirect passive ideation phrase
    "not wake up",
    "never wake up",
    "fall asleep and not",
    "go to sleep and not wake",
    "sleep and not wake up",
    # No future / no point continuing
    "no reason to keep going",
    "no reason to continue",
    "see no point in going on",
    "what's the point",
    "whats the point",
    "can't see a future",
    "cant see a future",
    "no future for myself",
    # Self-referential worthlessness / pointlessness — context-gated because
    # the bare words have common mundane uses ("this meeting was worthless",
    # "this rule is pointless") but are clinically significant when
    # self-referential and corroborated by other depression signals.
    "worthless",
    "pointless",
]

# ── Context-Gated Phrases ──────────────────────────────────────────────────
# These are a SUBSET of INDIRECT_IDEATION_PHRASES that are short and have
# common everyday uses (e.g. "tired of fighting traffic", "ready to go home",
# "want to disappear on vacation"). They should only trigger the indirect
# ideation floor when CORROBORATED by at least one of:
#   (a) another hit from MODERATE_RISK_KEYWORDS or MILD_NEGATIVE_KEYWORDS,
#   (b) ml_dep_prob >= 0.4  (model detects some depression signal),
#   (c) another *different* indirect ideation phrase also matched.
#
# IMPORTANT: Do NOT add phrases here just to suppress specific test cases.
# Only add phrases that are genuinely short/generic enough to appear in
# everyday non-crisis language. Longer, more specific phrases like
# "want to disappear forever" or "tired of living like this" should NOT
# be gated — they are specific enough to be clinically meaningful on their own.
CONTEXT_GATED_PHRASES = {
    "tired of fighting",
    "want to disappear",
    "ready to go",
    "ready to leave",
    "i'm done",
    "im done",
    "i am done",
    "what's the point",
    "whats the point",
    "want it to stop",
    # Self-referential worthlessness/pointlessness — gated so that
    # "this meeting was worthless" / "this rule is pointless" stay Low.
    "worthless",
    "pointless",
}

# ── Theme Mapping ──────────────────────────────────────────────────────────
# Used to extract themes from journal entries to populate user profiles for Peer Matching.
# Mirrored from frontend js/analyze.js.
THEME_MAP = [
    {"keywords": ["work", "job", "boss", "colleague", "office", "career"],   "theme": "Work & Career Stress"},
    {"keywords": ["family", "parent", "mother", "father", "sibling", "home"], "theme": "Family Relationships"},
    {"keywords": ["friend", "social", "alone", "lonely", "isolated"],         "theme": "Social & Loneliness"},
    {"keywords": ["school", "study", "exam", "university", "college"],        "theme": "Academic Pressure"},
    {"keywords": ["health", "sick", "pain", "doctor", "illness"],             "theme": "Health Concerns"},
    {"keywords": ["money", "financial", "debt", "bills", "broke"],            "theme": "Financial Stress"},
    {"keywords": ["relationship", "partner", "boyfriend", "girlfriend", "breakup", "divorce"], "theme": "Relationship Issues"},
    {"keywords": ["sleep", "tired", "insomnia", "rest", "exhausted"],         "theme": "Sleep & Energy"},
    {"keywords": ["future", "hope", "goal", "dream", "plan"],                 "theme": "Future Outlook"},
    {"keywords": ["anxiety", "panic", "worry", "fear", "nervous"],            "theme": "Anxiety & Fear"},
    {"keywords": ["happy", "grateful", "joy", "love", "excited"],             "theme": "Positive Emotions"},
]
