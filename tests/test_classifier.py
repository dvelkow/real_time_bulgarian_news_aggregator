import pytest

from classifier import classify


@pytest.mark.parametrize('title, expected', [
    # Keywords inside unrelated words must not match (all misfiled before, seen live on 2026-10-25)
    ('7,24 % е избирателната активност в област Монтана към 11 часа', 'other'),  # 'внос' in 'активност'
    ('Испанският крал Фелипе VI претърпя операция на очите', 'health'),         # 'ски' in 'Испанският'
    ('Шефът на Ryanair предупреди за по-скъпи билети', 'other'),                 # 'AI' in 'Ryanair'
    ('Нов транспортен план за София', 'other'),                                  # 'спорт' in 'транспорт'
    ('Времето днес', 'other'),                                                   # 'ЕС' in 'днес'
    # Stems still match inflected forms
    ('Парламентарните избори започнаха', 'politics'),
    ('142-ма са арестувани при протестите в Париж', 'crime'),
    # Acronyms match as whole words
    ('Лидерите на ЕС се срещат в Брюксел', 'politics'),
    ('Левски победи ЦСКА в дербито', 'sports'),
    ('Нов рекорд при COVID-19 ваксините', 'health'),
])
def test_classify(title, expected):
    assert classify(title) == expected
