import requests
from bs4 import BeautifulSoup
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            host=os.getenv('MYSQL_HOST'),
            database=os.getenv('MYSQL_DATABASE')
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error: {e}")
        return None

def fetch_news():
    sources = [
        {'url': 'https://www.dnevnik.bg/', 'source_name': 'Dnevnik'},
        {'url': 'https://novini.bg/', 'source_name': 'Novini'},
        {'url': 'https://www.24chasa.bg/', 'source_name': '24 Chasa'},
        {'url': 'https://nova.bg/news', 'source_name': 'Nova'},
        {'url': 'https://bntnews.bg/', 'source_name': 'BNT News'}
    ]

    for source in sources:
        url = source['url']
        source_name = source['source_name']
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        if source_name == 'Dnevnik':
            articles = soup.find_all('div', class_='article')
            for article in articles:
                title_tag = article.find('h3')
                if title_tag:
                    title = title_tag.text.strip()
                    link = title_tag.find('a')['href']
                    link = url + link if not link.startswith('http') else link
                    published_tag = article.find('time')
                    published = published_tag['datetime'] if published_tag else 'Unknown'

                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO articles (title, link, published, source) VALUES (%s, %s, %s, %s)",
                            (title, link, published, source_name)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()

        elif source_name == 'Novini':
            articles = soup.find_all('div', class_='article-item')
            for article in articles:
                title_tag = article.find('h3', class_='article-title')
                if title_tag:
                    title = title_tag.text.strip()
                    link = title_tag.find('a')['href']
                    link = url + link if not link.startswith('http') else link
                    published_tag = article.find('time', class_='article-date')
                    published = published_tag['datetime'] if published_tag else 'Unknown'

                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO articles (title, link, published, source) VALUES (%s, %s, %s, %s)",
                            (title, link, published, source_name)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()

        # Add similar blocks for other sources, adjusting the selectors as needed
        elif source_name == '24 Chasa':
            # Adjust the following selectors based on the actual HTML structure of 24chasa.bg
            articles = soup.find_all('div', class_='news-card')
            for article in articles:
                title_tag = article.find('a', class_='title')
                if title_tag:
                    title = title_tag.text.strip()
                    link = title_tag['href']
                    link = url + link if not link.startswith('http') else link
                    published_tag = article.find('span', class_='date')
                    published = published_tag.text.strip() if published_tag else 'Unknown'

                    # Store in MySQL
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO articles (title, link, published, source) VALUES (%s, %s, %s, %s)",
                            (title, link, published, source_name)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()

        elif source_name == 'Nova':
            # Adjust the following selectors based on the actual HTML structure of Nova.bg
            articles = soup.find_all('div', class_='news-card')
            for article in articles:
                title_tag = article.find('a', class_='title')
                if title_tag:
                    title = title_tag.text.strip()
                    link = title_tag['href']
                    link = url + link if not link.startswith('http') else link
                    published_tag = article.find('span', class_='date')
                    published = published_tag.text.strip() if published_tag else 'Unknown'

                    # Store in MySQL
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO articles (title, link, published, source) VALUES (%s, %s, %s, %s)",
                            (title, link, published, source_name)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()

    
        elif source_name == 'BNT News':
            # Adjust the following selectors based on the actual HTML structure of BNT News
            articles = soup.find_all('div', class_='news-item')
            for article in articles:
                title_tag = article.find('h2')
                if title_tag:
                    title = title_tag.text.strip()
                    link = article.find('a')['href']
                    link = url + link if not link.startswith('http') else link
                    published_tag = article.find('time')
                    published = published_tag['datetime'] if published_tag else 'Unknown'

                    # Store in MySQL
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO articles (title, link, published, source) VALUES (%s, %s, %s, %s)",
                            (title, link, published, source_name)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()


if __name__ == '__main__':
    fetch_news()
