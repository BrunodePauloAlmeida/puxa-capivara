from puxa.texto import normalizar_nome, semelhanca, slugify


def test_normalizar_nome_remove_acento_pontuacao_e_espacos():
    assert normalizar_nome("  José da Silva-Júnior ") == "JOSE DA SILVA JUNIOR"
    assert normalizar_nome(None) == ""


def test_semelhanca_ignora_particulas():
    assert semelhanca("Alan Rick Miranda", "ALAN RICK MIRANDA") == 1.0
    assert semelhanca("Maria das Dores Souza", "Maria Souza") == 2 / 3
    assert semelhanca("Fulano", "") == 0.0


def test_slugify():
    assert slugify("Tabata Amaral") == "tabata-amaral"
    assert slugify("Lula") == "lula"
    assert slugify("Dr. João Ávila (PR)") == "dr-joao-avila-pr"
