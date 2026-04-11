"""
Room/Hall auto-classification for ADR-145 MemPalace.

Classifies memories into room (topic) and hall (knowledge type) using
keyword heuristics. Falls back to "general" room and "fact" hall when
no clear match is found.

This avoids an additional LLM call per fact (~50 tokens) while providing
reasonable classification accuracy. LLM-based classification can be added
as an enhancement later.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── Hall definitions (knowledge type) ──
# Order matters: first match wins
HALL_PATTERNS: list[tuple[str, list[str]]] = [
    ("warning", [
        r"\bdon'?t\b", r"\bnever\b", r"\bavoid\b", r"\bdanger", r"\brisk",
        r"\bcaution", r"\bwarning", r"\bcareful", r"\bdo not\b", r"\bforbid",
        r"\bprohibit", r"\billegal", r"\bpenalt", r"\bfine\b",
    ]),
    ("decision", [
        r"\bdecid", r"\bchose\b", r"\bchosen\b", r"\bapproved?\b", r"\brejected?\b",
        r"\bagreed\b", r"\bselected?\b", r"\bpicked\b", r"\bwent with\b",
        r"\bswitched? to\b", r"\bmigrat", r"\badopted?\b", r"\bresolved?\b",
    ]),
    ("procedure", [
        r"\bstep\s*\d", r"\bfirst\b.*\bthen\b", r"\bprocess\b", r"\bworkflow\b",
        r"\bhow to\b", r"\bprocedure\b", r"\binstructions?\b", r"\brecipe\b",
        r"\brun\b.*\bcommand\b", r"\bexecute\b", r"\bsetup\b", r"\binstall\b",
    ]),
    ("event", [
        r"\bhappened\b", r"\boccurred\b", r"\bmeeting\b", r"\bcall\b",
        r"\bincident\b", r"\boutage\b", r"\breleased?\b", r"\blaunched?\b",
        r"\bdeployed?\b", r"\bstarted?\b", r"\bfinished?\b", r"\bcompleted?\b",
        r"\bon \d{4}-\d{2}-\d{2}\b", r"\byesterday\b", r"\blast week\b",
    ]),
    ("preference", [
        r"\bprefer", r"\blike[sd]?\b", r"\bfavorite\b", r"\bwant[sed]?\b",
        r"\brather\b", r"\bstyle\b", r"\btaste\b", r"\bchoice\b",
    ]),
    ("discovery", [
        r"\bfound\b", r"\bdiscover", r"\blearned\b", r"\brealized?\b",
        r"\bturns out\b", r"\bnoticed\b", r"\binsight\b", r"\bresearch",
        r"\banalysis\b", r"\bbenchmark",
    ]),
    # Default: "fact" — captured by no-match fallback
]

# ── Room definitions (topic) ──
ROOM_PATTERNS: list[tuple[str, list[str]]] = [
    ("auth", [
        r"\bauth", r"\blogin", r"\bjwt\b", r"\btoken", r"\bsession",
        r"\bpassword", r"\bcredential", r"\boauth", r"\bsso\b", r"\bsign[- ]?in\b",
    ]),
    ("pipeline", [
        r"\bpipeline", r"\bci/?cd\b", r"\bbuild\b", r"\bdeploy", r"\bgithub action",
        r"\bjenkins", r"\bcircleci", r"\bworkflow\b.*\bautomat",
    ]),
    ("infrastructure", [
        r"\bserver", r"\bnginx\b", r"\bpm2\b", r"\bdocker", r"\bk8s\b",
        r"\bkubernet", r"\binfra", r"\baws\b", r"\bgcp\b", r"\bazure\b",
        r"\bvps\b", r"\bload balanc", r"\bdns\b", r"\bssl\b", r"\bcert\b",
    ]),
    ("deployment", [
        r"\bdeploy", r"\brelease\b", r"\brollback", r"\bhotfix",
        r"\bstaging\b", r"\bproduction\b", r"\bblue[- ]?green",
    ]),
    ("schema", [
        r"\bschema", r"\bmigrat", r"\bcolumn\b", r"\btable\b", r"\bindex\b",
        r"\bpostgres", r"\bdatabase\b", r"\bsql\b", r"\bquery\b",
        r"\balembic", r"\bforeign key",
    ]),
    ("api", [
        r"\bapi\b", r"\bendpoint", r"\broute\b", r"\brest\b", r"\bgraphql",
        r"\bhttp\b", r"\brequest\b", r"\bresponse\b", r"\bwebhook",
    ]),
    ("ui", [
        r"\bui\b", r"\bfrontend", r"\breact\b", r"\bcomponent", r"\bcss\b",
        r"\bbutton\b", r"\bmodal\b", r"\bpanel\b", r"\blayout\b",
        r"\bdesign\b", r"\bux\b", r"\bstyle\b",
    ]),
    ("tax", [
        r"\btax", r"\bfiling\b", r"\bird\b", r"\bmpf\b", r"\bprofit",
        r"\bdeduction", r"\bexempt", r"\btaxable\b", r"\breturn\b.*\btax",
    ]),
    ("hr", [
        r"\bhr\b", r"\bhuman resource", r"\bsalary", r"\bleave\b",
        r"\bemployee", r"\bhiring", r"\brecruitment", r"\bonboarding",
    ]),
    ("legal", [
        r"\blegal", r"\bcontract", r"\bclause\b", r"\blawyer",
        r"\blitigation", r"\bcourt\b", r"\bregulat", r"\blicense\b",
    ]),
    ("compliance", [
        r"\bcompliance", r"\baudit\b", r"\bregulat", r"\bkyc\b",
        r"\baml\b", r"\bgdpr\b", r"\bprivacy\b", r"\bdata protect",
    ]),
    ("monitoring", [
        r"\bmonitor", r"\balert", r"\bmetric", r"\blog[sg]?\b",
        r"\bgrafana\b", r"\bprometheus\b", r"\bobservab", r"\btrac[ei]",
    ]),
    ("agent", [
        r"\bagent\b", r"\bllm\b", r"\bai\b", r"\bmemory\b.*\bsystem\b",
        r"\bhindsight\b", r"\bprompt\b", r"\btool\b.*\bcall\b",
        r"\bpes\b", r"\bspell\b", r"\borchestrat",
    ]),
    # Default: "general" — captured by no-match fallback
]


def _match_patterns(text: str, patterns: list[tuple[str, list[str]]]) -> str | None:
    """Match text against pattern list, return first matching category or None."""
    text_lower = text.lower()
    for category, regexes in patterns:
        for pattern in regexes:
            if re.search(pattern, text_lower):
                return category
    return None


def classify_room_hall(
    fact_text: str,
    context: str | None = None,
    existing_room: str | None = None,
    existing_hall: str | None = None,
) -> tuple[str, str]:
    """
    Classify a fact into room (topic) and hall (knowledge type).

    If existing values are provided, they are kept as-is.
    Otherwise, keyword heuristics determine the classification.

    Args:
        fact_text: The fact text to classify
        context: Optional context string for additional signals
        existing_room: Pre-assigned room (kept if not None)
        existing_hall: Pre-assigned hall (kept if not None)

    Returns:
        Tuple of (room, hall)
    """
    combined = f"{fact_text} {context or ''}"

    room = existing_room
    if room is None:
        room = _match_patterns(combined, ROOM_PATTERNS) or "general"

    hall = existing_hall
    if hall is None:
        hall = _match_patterns(combined, HALL_PATTERNS) or "fact"

    return room, hall


def classify_facts_batch(facts: list) -> None:
    """
    Classify room/hall for a batch of ProcessedFact or ExtractedFact objects.

    Modifies facts in-place. Only sets room/hall if not already set.
    """
    for fact in facts:
        fact_text = getattr(fact, 'fact_text', '') or getattr(fact, 'text', '') or ''
        context = getattr(fact, 'context', None)
        room, hall = classify_room_hall(
            fact_text,
            context,
            existing_room=getattr(fact, 'room', None),
            existing_hall=getattr(fact, 'hall', None),
        )
        fact.room = room
        fact.hall = hall
