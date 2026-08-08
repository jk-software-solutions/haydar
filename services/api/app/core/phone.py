import re


def normalize_e164(value: str) -> str:
    """Normalize a strict international phone identifier to E.164 form."""

    candidate = value.strip()
    if not candidate.startswith("+"):
        raise ValueError("phone must include an international country code, for example +966")
    digits = re.sub(r"[\s().-]", "", candidate[1:])
    if not digits.isdigit() or digits.startswith("0") or not 8 <= len(digits) <= 15:
        raise ValueError("phone must be a valid E.164 international number")
    return f"+{digits}"
