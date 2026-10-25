from importance import hot_words

ROWS = [
    ('Президентът Радев гласува', 'Dnevnik'),
    ('Румен Радев: Гласувах за България', '24chasa'),
    ('Гласувах, каза Радев пред България', 'Fakti'),
    ('Днес Илияна Йотова гласува в България', 'Sega'),
    ('Вот: и Илияна Йотова гласува', 'Fakti'),
    ('Как гласува Илияна Йотова', 'Dnevnik'),
    ('Борисов: Гласувах', 'Sega'),
    ('Бойко Борисов отказа', 'Dnevnik'),
]


def test_hot_words_are_names_three_outlets_use():
    hot = {h['word']: h for h in hot_words(ROWS)}

    assert {w for w, h in hot.items() if h['alias_of'] is None} == {'Радев', 'Йотова'}
    assert hot['Радев']['sources'] == 3 and hot['Радев']['titles'] == 3
    # Always next to the surname, so it is boxed with it but not listed on its own
    assert hot['Илияна']['alias_of'] == 'Йотова'
    # 3 outlets, but only ever opens a sentence ("Радев: Гласувах ...") — a verb, not a name
    assert 'Гласувах' not in hot
    # Too generic for a Bulgarian aggregator
    assert 'България' not in hot
    # Only 2 outlets
    assert 'Борисов' not in hot


def test_hot_words_limit_counts_main_words_only():
    assert [h['word'] for h in hot_words(ROWS, limit=1) if h['alias_of'] is None] == ['Йотова']


def test_no_hot_words_without_enough_outlets():
    assert hot_words(ROWS[:2]) == []
