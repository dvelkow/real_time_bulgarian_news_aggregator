import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

print("Importing fetch_news.py")  # Diagnostic print

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
            print("Successfully connected to the database")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    return None

def fetch_24chasa_news(limit=10):
    url = 'https://www.24chasa.bg/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    count = 0

    for item in soup.find_all('div', class_='header-news'):
        if count >= limit:
            break
        title_tag = item.find('h3', class_='title')
        if title_tag and title_tag.a:
            title = title_tag.a.text.strip()
            link = title_tag.a['href']
            link = "https://www.24chasa.bg" + link if link.startswith('/') else link
            date_element = item.find('time', class_='time')
            if date_element and date_element.get('datetime'):
                date_str = date_element['datetime'].strip()
                published = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z')
            else:
                published = datetime.now(pytz.timezone('Europe/Sofia'))
            print(f"Fetched 24chasa article: {title}, Published: {published}")  # Debug print
            articles.append((title, link, published, '24chasa'))
            count += 1
    return articles

def fetch_dnevnik_news(limit=10):
    url = 'https://www.dnevnik.bg/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    count = 0
    for item in soup.find_all('article'):
        if count >= limit:
            break
        h3_tag = item.find('h3')
        if h3_tag:
            title = h3_tag.text.strip()
            link = item.find('a')['href']
            date_element = item.find('time')
            if date_element and date_element.get('datetime'):
                published = datetime.fromisoformat(date_element['datetime'].replace('Z', '+00:00'))
                published = published.astimezone(pytz.timezone('Europe/Sofia'))
            else:
                published = datetime.now(pytz.timezone('Europe/Sofia'))
            print(f"Fetched Dnevnik article: {title}, Published: {published}")  # Debug print
            articles.append((title, link, published, 'Dnevnik'))
            count += 1
    return articles

def delete_all_articles(connection):
    try:
        cursor = connection.cursor()
        query = "DELETE FROM articles"
        cursor.execute(query)
        connection.commit()
        print(f"Deleted all articles")
    except Error as e:
        print(f"Error deleting articles: {e}")
    finally:
        if cursor:
            cursor.close()

def insert_articles_to_db(articles, connection):
    cursor = connection.cursor()
    query = """
    INSERT INTO articles (title, link, published, source)
    VALUES (%s, %s, %s, %s)
    """
    try:
        for article in articles:
            title, link, published, source = article
            cursor.execute("SELECT COUNT(*) FROM articles WHERE title = %s", (title,))
            if cursor.fetchone()[0] == 0:
                print(f"Inserting article: {article}")  # Debug print
                cursor.execute(query, (title, link, published, source))
        connection.commit()
        print(f"Inserted {len(articles)} new articles")
    except Error as e:
        print(f"Error inserting articles: {e}")
        connection.rollback()
    finally:
        cursor.close()

def fetch_news():
    all_articles = []
    all_articles.extend(fetch_24chasa_news(limit=10))
    all_articles.extend(fetch_dnevnik_news(limit=10))
    return all_articles

def update_news_database():
    connection = get_database_connection()
    if connection:
        delete_all_articles(connection)
        articles = fetch_news()
        insert_articles_to_db(articles, connection)
        connection.close()
        return len(articles)
    return 0

if __name__ == "__main__":
    articles = fetch_news()
    for article in articles:
        print(f"Title: {article[0]}")
        print(f"Link: {article[1]}")
        print(f"Published: {article[2]}")
        print(f"Source: {article[3]}")
        print("---")
    
    # Update the database with fetched articles
    print(f"Updated {update_news_database()} articles")
