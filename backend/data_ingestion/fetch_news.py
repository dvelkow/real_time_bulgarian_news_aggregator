import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
from abc import ABC, abstractmethod

load_dotenv()

class NewsFetcher(ABC):
    def __init__(self, source, url, limit):
        self.source = source
        self.url = url
        self.limit = limit

    @abstractmethod
    def fetch_articles(self):
        pass

    def get_soup(self):
        response = requests.get(self.url)
        return BeautifulSoup(response.content, 'html.parser')

    def localize_time(self, dt):
        return pytz.timezone('Europe/Sofia').localize(dt)

class Chasa24NewsFetcher(NewsFetcher):
    def __init__(self, limit=3):
        super().__init__('24chasa', 'https://www.24chasa.bg/', limit)

    def fetch_articles(self):
        soup = self.get_soup()
        articles = []
        count = 0

        news_sections = [
            soup.find('section', class_='important-news-container'),
            soup.find('div', class_='main-grid')
        ]

        for section in news_sections:
            if section:
                for item in section.find_all('article'):
                    if count >= self.limit:
                        return articles

                    title_tag = item.find('h3', class_='title')
                    if title_tag and title_tag.a:
                        title = title_tag.a.text.strip()
                        link = title_tag.a['href']
                        if not link.startswith('http'):
                            link = f'{self.url}{link}'

                        time_element = item.find('time', class_='time')
                        if time_element:
                            time_str = time_element.text.strip()
                            date_str = f"{datetime.now().year}-{datetime.now().month:02d}-{datetime.now().day:02d} {time_str}"
                            try:
                                published = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                                published = self.localize_time(published)
                            except ValueError:
                                published = self.localize_time(datetime.now())
                        else:
                            published = self.localize_time(datetime.now())

                        print(f"Fetched {self.source} article: {title}, Published: {published}")
                        articles.append((title, link, published, self.source))
                        count += 1

        return articles

class DnevnikNewsFetcher(NewsFetcher):
    def __init__(self, limit=10):
        super().__init__('Dnevnik', 'https://www.dnevnik.bg/', limit)

    def fetch_articles(self):
        soup = self.get_soup()
        articles = []
        count = 0
        for item in soup.find_all('article'):
            if count >= self.limit:
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
                    published = self.localize_time(datetime.now())
                print(f"Fetched {self.source} article: {title}, Published: {published}")
                articles.append((title, link, published, self.source))
                count += 1
        return articles

class FaktiNewsFetcher(NewsFetcher):
    def __init__(self, limit=3):
        super().__init__('Fakti', 'https://fakti.bg/', limit)

    def fetch_articles(self):
        soup = self.get_soup()
        articles = []
        count = 0

        for item in soup.find_all('article', class_='panel selected-ln'):
            if count >= self.limit:
                break
            title_tag = item.find('span', class_='article-title')
            if title_tag:
                title = title_tag.text.strip()
                link = item.find('a')['href']
                link = f"{self.url}{link}" if link.startswith('/') else link
                date_element = item.find('div', class_='ndt')
                if date_element:
                    date_str = date_element.text.strip()
                    try:
                        published = datetime.strptime(date_str, 'днес в %H:%M ч.')
                        published = published.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
                        published = self.localize_time(published)
                    except ValueError:
                        published = self.localize_time(datetime.now())
                else:
                    published = self.localize_time(datetime.now())
                print(f"Fetched {self.source} article: {title}, Published: {published}")
                articles.append((title, link, published, self.source))
                count += 1

        return articles

class NewsAggregator:
    @classmethod
    def fetch_all_news(cls):
        fetchers = [
            Chasa24NewsFetcher(limit=3),
            DnevnikNewsFetcher(limit=10),
            FaktiNewsFetcher(limit=3)
        ]
        all_articles = []
        for fetcher in fetchers:
            all_articles.extend(fetcher.fetch_articles())
        return all_articles

    @classmethod
    def update_news_database(cls):
        connection = cls.get_database_connection()
        if connection:
            cls.delete_all_articles(connection)
            articles = cls.fetch_all_news()
            cls.insert_articles_to_db(articles, connection)
            connection.close()
            return len(articles)
        return 0

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
                    print(f"Inserting article: {article}")
                    cursor.execute(query, (title, link, published, source))
            connection.commit()
            print(f"Inserted {len(articles)} new articles")
        except Error as e:
            print(f"Error inserting articles: {e}")
            connection.rollback()
        finally:
            cursor.close()

if __name__ == "__main__":
    articles = NewsAggregator.fetch_all_news()
    for article in articles:
        print(f"Title: {article[0]}")
        print(f"Link: {article[1]}")
        print(f"Published: {article[2]}")
        print(f"Source: {article[3]}")
        print("---")
    
    print(f"Updated {NewsAggregator.update_news_database()} articles")