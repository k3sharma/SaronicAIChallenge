"""
This file is a DLP redaction check that scans tool output for patterns that look like sensitive data (e.g. SSNs) 
and redacts them before that output goes back to Claude, into the audit log, or to the end user.
"""
# Use regex for pattern-matching
import re

# One pattern format: 3 digits, dash, 2 digits, dash, 4 digits (the standard US SSN display format)
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

def redact_sensitive_data(value):
    # Use recursion to correctly handle a dict inside a dict, list of strings, etc.
    # Traverses a value (of any data type) and returns a version with any SSN-shaped substrings replaced by a redaction marker
    # The original value will be untouched
    if isinstance(value, str):
        return SSN_PATTERN.sub("***-**-****", value)
    elif isinstance(value, dict):
        return {key: redact_sensitive_data(v) for key, v in value.items()}
    elif isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    else:
        # Anything else (int, bool, None, etc.) can't contain an SSN pattern, so it passes through unchanged
        return value


def contains_sensitive_data(value) -> bool:
    # Tells whether redact_sensitive_data would change anything
    # Useful for the audit log because we want to record if the DLP redaction was activated
    redacted = redact_sensitive_data(value)
    return redacted != value