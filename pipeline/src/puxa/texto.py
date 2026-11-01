"""Normalização de nomes para cruzar fontes que escrevem o mesmo nome de jeitos diferentes."""

import re
import unicodedata

_PARTICULAS = {"DA", "DAS", "DE", "DO", "DOS", "E"}


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def normalizar_nome(nome: str | None) -> str:
    """'José  da Silva Júnior' -> 'JOSE DA SILVA JUNIOR'."""
    if not nome:
        return ""
    texto = sem_acento(nome).upper()
    texto = re.sub(r"[^A-Z ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _grafia_canonica(parte: str) -> str:
    """Aproxima grafias que as fontes alternam: SOUZA/SOUSA, THEREZA/TEREZA, LUIZ/LUIS, MATTOS/MATOS."""
    parte = parte.replace("PH", "F").replace("TH", "T").replace("Y", "I").replace("W", "V").replace("Z", "S")
    return re.sub(r"(.)\1+", r"\1", parte)


def tokens(nome: str | None) -> set[str]:
    """Partes significativas do nome, sem 'da', 'de', 'dos'..., com grafia aproximada."""
    return {_grafia_canonica(t) for t in normalizar_nome(nome).split() if t not in _PARTICULAS}


def semelhanca(a: str | None, b: str | None) -> float:
    """Índice de Jaccard entre as partes dos dois nomes (0 a 1)."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def slugify(texto: str) -> str:
    """'Tabata Amaral' -> 'tabata-amaral'."""
    base = sem_acento(texto).lower()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    return base.strip("-")
