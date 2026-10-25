"""
What counts as important in a headline.

- Hot words: names and places (capitalised words) that at least MIN_SOURCES different
  outlets used in the last WINDOW_HOURS — the stories everyone is covering right now.
- Urgent words: the few markers editors put on breaking news.

Readers add their own words in the browser; the front end boxes all three kinds.
"""

import re
from collections import defaultdict

URGENT_WORDS = ['извънредно', 'спешно', 'ексклузивно', 'официално', 'на живо', 'последно', 'внимание']

WINDOW_HOURS = 12
MIN_SOURCES = 3
HOT_LIMIT = 10

_TOKEN = re.compile(r'(?<!\w)[A-ZА-Я][\w-]{2,}')
_SENTENCE_START = set(':.!?„"“”«»—–-(')

# Capitalised, but not news on their own
_STOP_WORDS = {
    'Как', 'Какво', 'Каква', 'Какви', 'Защо', 'Кой', 'Коя', 'Кои', 'Кога', 'Къде', 'Колко',
    'Още', 'Ето', 'Това', 'Тази', 'Този', 'Тези', 'Нов', 'Нова', 'Ново', 'Нови',
    'След', 'При', 'Над', 'Под', 'Пред', 'Между', 'Без', 'Вече', 'Днес', 'Утре', 'Вчера',
    'Само', 'Сега', 'Видео', 'Снимки', 'Обновена', 'Фотогалерия', 'Галерия', 'Мнение',
    'Анализ', 'Интервю', 'Коментар', 'Live', 'Online',
}
_STOP_PREFIXES = ('Българ',)  # a Bulgarian aggregator mentions Bulgaria in every other title


def _is_stop(word: str) -> bool:
    return (word in _STOP_WORDS or word.capitalize() in _STOP_WORDS
            or word.startswith(_STOP_PREFIXES))


def hot_words(rows: list[tuple[str, str]], min_sources: int = MIN_SOURCES,
              limit: int = HOT_LIMIT) -> list[dict]:
    """
    rows: (title, source) pairs from the last WINDOW_HOURS, duplicates included.
    Returns the most widely covered words, most sources first:
        [{'word': 'Радев', 'sources': 6, 'titles': 10, 'alias_of': None}, ...]
    alias_of names the word this one always appears with ('Илияна' -> 'Йотова'); the
    front end boxes aliases too but leaves them out of the "горещо" list.
    """
    sources = defaultdict(set)
    titles = defaultdict(set)
    positions = defaultdict(list)
    # Seen capitalised mid-sentence at least once — so a name, not a verb that opens a quote ("Радев: Гласувах ...")
    mid_sentence = set()
    for i, (title, source) in enumerate(rows):
        for m in _TOKEN.finditer(title):
            word = m.group()
            if _is_stop(word):
                continue
            sources[word].add(source)
            titles[word].add(i)
            positions[word].append(m.start())
            before = title[:m.start()].rstrip()
            if before and before[-1] not in _SENTENCE_START:
                mid_sentence.add(word)

    def avg_position(word):
        return sum(positions[word]) / len(positions[word])

    # Ties go to the word later in the title, so 'Йотова' leads and 'Илияна' becomes its alias
    candidates = sorted(
        (w for w in sources if len(sources[w]) >= min_sources and w in mid_sentence),
        key=lambda w: (-len(sources[w]), -len(titles[w]), -avg_position(w), w),
    )

    result = []
    for word in candidates:
        alias_of = next(
            (r['word'] for r in result if r['alias_of'] is None and titles[word] <= titles[r['word']]),
            None,
        )
        result.append({
            'word': word,
            'sources': len(sources[word]),
            'titles': len(titles[word]),
            'alias_of': alias_of,
        })
        if sum(1 for r in result if r['alias_of'] is None) >= limit:
            break
    return result
