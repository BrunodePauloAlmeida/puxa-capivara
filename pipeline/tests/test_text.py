from puxa.text import normalize_name, similarity, slugify


def test_normalize_name_removes_accents_punctuation_and_spaces():
    assert normalize_name("  José da Silva-Júnior ") == "JOSE DA SILVA JUNIOR"
    assert normalize_name(None) == ""


def test_similarity_ignores_particles():
    assert similarity("Alan Rick Miranda", "ALAN RICK MIRANDA") == 1.0
    assert similarity("Maria das Dores Souza", "Maria Souza") == 2 / 3
    assert similarity("Fulano", "") == 0.0


def test_slugify():
    assert slugify("Tabata Amaral") == "tabata-amaral"
    assert slugify("Lula") == "lula"
    assert slugify("Dr. João Ávila (PR)") == "dr-joao-avila-pr"


def test_similarity_brings_alternative_spellings_together():
    assert similarity("PATRUS ANANIAS DE SOUZA", "PATRUS ANANIAS DE SOUSA") == 1.0
    assert similarity("ELCIONE THEREZINHA", "ELCIONE TEREZINHA") == 1.0
