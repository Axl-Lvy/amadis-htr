"""The single declared normalisation fold used by every folded figure.

Deliberately narrower than the matcher's `foldWord`: it removes only the
differences that are conventions of transcription rather than differences of
recognition. Anything it removed beyond that would hide real errors.
"""

import unicodedata

LONG_S = "ſ"


def fold(text: str) -> str:
    """Normalise text for a convention-insensitive comparison.

    NFC, long s to s, case folding, u and v collapsed to v, i and j collapsed
    to i. Whitespace is preserved, because line-break and word-boundary errors
    are real errors on this material.
    """
    out = unicodedata.normalize("NFC", text)
    out = out.replace(LONG_S, "s")
    out = out.casefold()
    out = out.replace("u", "v")
    return out.replace("j", "i")
