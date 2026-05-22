import re
from typing import Optional


class PIIRedactor:
    """Lightweight PII redaction using regex patterns.
    For production, use Presidio or similar library.
    This avoids the heavy spacy dependency for the Docker image.
    """

    PATTERNS = [
        # Email
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_REDACTED]'),
        # Phone numbers (various formats)
        (re.compile(r'\b(\+?1?[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'), '[PHONE_REDACTED]'),
        # SSN
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN_REDACTED]'),
        # Credit card numbers
        (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), '[CC_REDACTED]'),
        # IP addresses
        (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '[IP_REDACTED]'),
        # Dates of birth patterns (MM/DD/YYYY, DD-MM-YYYY)
        (re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'), '[DATE_REDACTED]'),
    ]

    def redact(self, text: Optional[str]) -> Optional[str]:
        """Redact PII from text."""
        if not text:
            return text

        redacted = text
        for pattern, replacement in self.PATTERNS:
            redacted = pattern.sub(replacement, redacted)

        return redacted


pii_redactor = PIIRedactor()
