import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

print("Importing fetch_news.py")

#loads mysql connection secure info
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

#fetching data from 24chasa.bg
def fetch_24chasa_news(limit=10):
    url = 'https://www.24chasa.bg/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    count = 0

    # Find all news sections
    news_sections = [
        soup.find('section', class_='important-news-container'),
        soup.find('div', class_='main-grid')
    ]

    for section in news_sections:
        if section:
            for item in section.find_all('article'):
                if count >= limit:
                    return articles

                title_tag = item.find('h3', class_='title')
                if title_tag and title_tag.a:
                    title = title_tag.a.text.strip()
                    link = title_tag.a['href']
                    if not link.startswith('http'):
                        link = 'https://www.24chasa.bg' + link

                    time_element = item.find('time', class_='time')
                    if time_element:
                        time_str = time_element.text.strip()
                        date_str = f"{datetime.now().year}-{datetime.now().month:02d}-{datetime.now().day:02d} {time_str}"
                        try:
                            published = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                            published = pytz.timezone('Europe/Sofia').localize(published)
                        except ValueError:
                            published = datetime.now(pytz.timezone('Europe/Sofia'))
                    else:
                        published = datetime.now(pytz.timezone('Europe/Sofia'))

                    print(f"Fetched 24chasa article: {title}, Published: {published}")  # Debug print
                    articles.append((title, link, published, '24chasa'))
                    count += 1

    return articles

#fetching data from dnevnik.bg
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

#fetching data from fakti.bg
def fetch_fakti_news(limit=10):
    url = 'https://fakti.bg/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    count = 0

    for item in soup.find_all('article', class_='panel selected-ln'):
        if count >= limit:
            break
        title_tag = item.find('span', class_='article-title')
        if title_tag:
            title = title_tag.text.strip()
            link = item.find('a')['href']
            link = "https://fakti.bg" + link if link.startswith('/') else link
            date_element = item.find('div', class_='ndt')
            if date_element:
                date_str = date_element.text.strip()
                try:
                    published = datetime.strptime(date_str, 'днес в %H:%M ч.')
                    published = published.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
                    published = pytz.timezone('Europe/Sofia').localize(published)
                except ValueError:
                    published = datetime.now(pytz.timezone('Europe/Sofia'))
            else:
                published = datetime.now(pytz.timezone('Europe/Sofia'))
            print(f"Fetched Fakti article: {title}, Published: {published}")  # Debug print
            articles.append((title, link, published, 'Fakti'))
            count += 1

    return articles

#deleting all previous articles we had, so the database stays relevant
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
            
#inserting all the new fetched articles into the database
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

#a function to fetch all the news
def fetch_news():
    all_articles = []
    all_articles.extend(fetch_24chasa_news(limit=10))
    all_articles.extend(fetch_dnevnik_news(limit=10))
    all_articles.extend(fetch_fakti_news(limit=10))
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

#displaying in the terminal every single fetched news article
if __name__ == "__main__":
    articles = fetch_news()
    for article in articles:
        print(f"Title: {article[0]}")
        print(f"Link: {article[1]}")
        print(f"Published: {article[2]}")
        print(f"Source: {article[3]}")
        print("---")
    
    print(f"Updated {update_news_database()} articles")