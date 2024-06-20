import requests
from bs4 import BeautifulSoup
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

def get_database_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def fetch_dnevnik_news():
    url = 'https://www.dnevnik.bg/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []

    for item in soup.find_all('article'):
        h3_tag = item.find('h3')
        if h3_tag: 
            title = h3_tag.text.strip()
            link = item.find('a')['href']
            published = datetime.now()
            articles.append((title, link, published, 'Dnevnik'))

    return articles

def fetch_novini_news():
    url = 'https://novini.bg/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []

    for item in soup.find_all('div', class_='news-item'):
        h2_tag = item.find('h2')
        if h2_tag:  # Ensure h2_tag is not None
            title = h2_tag.text.strip()
            link = item.find('a')['href']
            published = datetime.now()
            articles.append((title, link, published, 'Novini'))

    return articles


def insert_articles_to_db(articles):
    connection = get_database_connection()
    if connection is None:
        print("Failed to connect to the database.")
        return

    cursor = connection.cursor()
    query = """
        INSERT INTO articles (title, link, published, source)
        VALUES (%s, %s, %s, %s)
    """
    try:
        cursor.executemany(query, articles)
        connection.commit()
    except Error as e:
        print(f"Error inserting articles: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    all_articles = []
    all_articles.extend(fetch_dnevnik_news())
    all_articles.extend(fetch_novini_news())
    # all_articles.extend(fetch_24chasa_news())
    # all_articles.extend(fetch_nova_news())
    # all_articles.extend(fetch_bnt_news())

    insert_articles_to_db(all_articles)
    print(f"Inserted {len(all_articles)} articles into the database.")
