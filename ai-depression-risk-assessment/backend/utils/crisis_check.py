from constants.keywords import HIGH_RISK_KEYWORDS

def check_crisis_keywords(text: str) -> tuple[bool, list[str]]:
    """
    Checks if a message contains any explicit high-risk crisis keywords.
    Returns (True, [matched_keywords]) if crisis language is detected,
    otherwise (False, []).
    """
    lower = text.lower()
    matches = [kw for kw in HIGH_RISK_KEYWORDS if kw in lower]
    return (len(matches) > 0, matches)
