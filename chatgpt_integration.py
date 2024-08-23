import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def categorize_articles(titles):
    prompt = """ категоризирай всеки един от тези статии под: 'politics', 'sports', or 'others'. 
    Следвай тези правила:
    1. Ако името на политик от партия е споменато, или война, или нещо общо с политика категоризирай като 'politics'.
    2. Ако става дума за футбул, футбулни резултати, Лудогорец, Левски, ЦСКА, или друг спорт категоризирай го като 'sports'.
    3. Всичко което не пада под тези 2 категоризирай като 'others'.
    ОТГОВОРИ САМО С КАТЕГОРИЯТА ЗА ВСЯКО ЗАГЛАВИЕ, ВСЯКА КАТЕГОРИЯ НА НОВ РЕД:

    """
    prompt += "\n".join(titles)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that categorizes news articles."},
            {"role": "user", "content": prompt}
        ]
    )

    categories = response.choices[0].message.content.strip().split('\n')
    return categories