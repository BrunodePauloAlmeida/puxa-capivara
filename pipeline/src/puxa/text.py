"""Name normalization to match sources that spell the same name in different ways."""

import re
import unicodedata

_PARTICLES = {"DA", "DAS", "DE", "DO", "DOS", "E"}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_name(name: str | None) -> str:
    """'José  da Silva Júnior' -> 'JOSE DA SILVA JUNIOR'."""
    if not name:
        return ""
    text = strip_accents(name).upper()
    text = re.sub(r"[^A-Z ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _canonical_spelling(part: str) -> str:
    """Brings together spellings that sources alternate: SOUZA/SOUSA, THEREZA/TEREZA, LUIZ/LUIS, MATTOS/MATOS."""
    part = part.replace("PH", "F").replace("TH", "T").replace("Y", "I").replace("W", "V").replace("Z", "S")
    return re.sub(r"(.)\1+", r"\1", part)


def tokens(name: str | None) -> set[str]:
    """Meaningful parts of the name, without 'da', 'de', 'dos'..., with approximate spelling."""
    return {_canonical_spelling(t) for t in normalize_name(name).split() if t not in _PARTICLES}


def similarity(a: str | None, b: str | None) -> float:
    """Jaccard index between the parts of the two names (0 to 1)."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def slugify(text: str) -> str:
    """'Tabata Amaral' -> 'tabata-amaral'."""
    base = strip_accents(text).lower()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    return base.strip("-")


_VOWELS = set("AEIOUÁÉÍÓÚÂÊÔÃÕÀÜ")


def display_name(name: str | None) -> str:
    """All-caps names (TSE standard) become 'Tarcísio Gomes de Freitas'. Acronyms without vowels ('JHC') and
    names that already come in mixed case ('Hugo Motta') stay as they are."""
    if not name or name != name.upper():
        return name or ""
    words = []
    for i, word in enumerate(name.split()):
        if not set(word) & _VOWELS:
            words.append(word)
        elif i > 0 and word in _PARTICLES:
            words.append(word.lower())
        else:
            words.append("-".join(p[:1] + p[1:].lower() for p in word.split("-")))
    return " ".join(words)
