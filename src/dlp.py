"""
This file is a DLP redaction check that scans tool output for patterns that look like sensitive data (e.g. SSNs) 
and redacts them before that output goes back to Claude, into the audit log, or to the end user.
"""
# Use regex for pattern-matching
import re

# Now, we have 5 patterns instead of just the SSN
# Interesting trade off occurs: 
# Broadening the SSN pattern to accept dots, spaces, or no separator at all catches more real SSNs, but it also makes the pattern more likely to false-positive on things that look like an SSN
# This is inherent to a regex-based DLP
# A production system would pair this with a dedicated DLP service or a classifier that considers context to manage that trade off better than regex alone ever can
SENSITIVE_PATTERNS = {
    # Broadened from the original dash-only version to also catch dots, spaces, or no separator at all 
    # ("987.65.4321", "987 65 4321", and "987654321") not just "987-65-4321"
    "ssn": re.compile(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    # Now, catches common API key shapes 
    # Anthropic("sk-ant-..."), OpenAI ("sk-..."), and AWS ("AKIA...")
    "api_key": re.compile(r"\b(?:sk-[a-zA-Z0-9_-]{10,}|AKIA[0-9A-Z]{16})\b"),
}

REDACTION_MARKERS = {
    "ssn": "***-**-****",
    "credit_card": "[REDACTED CARD NUMBER]",
    "email": "[REDACTED EMAIL]",
    "phone": "[REDACTED PHONE]",
    "api_key": "[REDACTED API KEY]",
}

def redact_sensitive_data(value):
    # Use recursion to correctly handle a dict inside a dict, list of strings, etc.
    # Traverses a value (of any data type) and returns a version with any SSN-shaped substrings replaced by a redaction marker
    # The original value will be untouched
    if isinstance(value, str):
        redacted = value    
        for name, pattern in SENSITIVE_PATTERNS.items():        # Now check every pattern in SENSITIVE_PATTERNS
            redacted = pattern.sub(REDACTION_MARKERS[name], redacted)
        return redacted
    elif isinstance(value, dict):
        return {key: redact_sensitive_data(v) for key, v in value.items()}
    elif isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    else:
        # Anything else (int, bool, None, etc.) can't contain an SSN pattern, so it passes through unchanged
        return value
    
# Reports which categories of sensitive data were found in a value (e.g. SSN or email)
# Use recursion method similar to redact_sensitive_data
def find_sensitive_categories(value) -> set[str]:
    found: set[str] = set()     # Create a new set of strings
    
    def _scan(v):
        if isinstance(v, str):
            for name, pattern in SENSITIVE_PATTERNS.items():
                if pattern.search(v):
                    found.add(name)
        elif isinstance(v, dict):
            for item in v.values():
                _scan(item)
        elif isinstance(v, list):
            for item in v:
                _scan(item)
    _scan(value)
    return found


def contains_sensitive_data(value) -> bool:
    # Now, we can just call find_sensitive_categories and ask "was anything found at all?"
    return len(find_sensitive_categories(value)) > 0