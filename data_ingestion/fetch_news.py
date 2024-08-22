import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
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
        return BeautifulSoup(requests.get(self.url).content, 'html.parser')

    def localize_time(self, dt):
        return pytz.timezone('Europe/Sofia').localize(dt)

class Chasa24NewsFetcher(NewsFetcher):
    def fetch_articles(self):
        soup = self.get_soup()
        articles = []
        count = 0
        for section in [soup.find('section', class_='important-news-container'), soup.find('div', class_='main-grid')]:
            if section:
                for item in section.find_all('article'):
                    if count >= self.limit:
                        return articles
                    title_tag = item.find('h3', class_='title')
                    if title_tag and title_tag.a:
                        title = title_tag.a.text.strip()
                        link = f"{self.url}{title_tag.a['href']}" if not title_tag.a['href'].startswith('http') else title_tag.a['href']
                        time_element = item.find('time', class_='time')
                        published = self.parse_date(time_element.text.strip()) if time_element else self.localize_time(datetime.now())
                        print(f"Fetched {self.source} article: {title}, Published: {published}")
                        articles.append((title, link, published, self.source))
                        count += 1
        return articles

    def parse_date(self, date_str):
        now = datetime.now()
        if ',' in date_str:
            date_part, time_part = date_str.split(',')
            day, month, year = map(int, date_part.split('.'))
            hour, minute = map(int, time_part.strip().split(':'))
            published = datetime(year, month, day, hour, minute)
        else:
            hour, minute = map(int, date_str.strip().split(':'))
            published = now.replace(hour=hour, minute=minute)
            if published > now:
                published -= timedelta(days=1)
        return self.localize_time(published)

class DnevnikNewsFetcher(NewsFetcher):
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
                    published = datetime.fromisoformat(date_element['datetime'].replace('Z', '+00:00')).astimezone(pytz.timezone('Europe/Sofia'))
                else:
                    published = self.localize_time(datetime.now())
                print(f"Fetched {self.source} article: {title}, Published: {published}")
                articles.append((title, link, published, self.source))
                count += 1
        return articles

class FaktiNewsFetcher(NewsFetcher):
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
                link = f"{self.url}{item.find('a')['href']}" if item.find('a')['href'].startswith('/') else item.find('a')['href']
                date_element = item.find('div', class_='ndt')
                published = self.parse_date(date_element.text.strip()) if date_element else self.localize_time(datetime.now())
                print(f"Fetched {self.source} article: {title}, Published: {published}")
                articles.append((title, link, published, self.source))
                count += 1
        return articles

    def parse_date(self, date_str):
        now = datetime.now()
        if 'вчера' in date_str:
            date = now - timedelta(days=1)
        elif 'днес' in date_str:
            date = now
        else:
            return self.localize_time(now)
        time_str = date_str.split('в')[-1].strip().replace('ч.', '').strip()
        time = datetime.strptime(time_str, '%H:%M')
        return self.localize_time(date.replace(hour=time.hour, minute=time.minute))

class NewsAggregator:
    @classmethod
    def fetch_all_news(cls):
        fetchers = [
            Chasa24NewsFetcher('24chasa', 'https://www.24chasa.bg/', 10), 
            DnevnikNewsFetcher('Dnevnik', 'https://www.dnevnik.bg/', 20),  
            FaktiNewsFetcher('Fakti', 'https://fakti.bg/', 10) 
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
            cursor.execute("DELETE FROM articles")
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
        query = "INSERT INTO articles (title, link, published, source) VALUES (%s, %s, %s, %s)"
        try:
            for article in articles:
                cursor.execute("SELECT COUNT(*) FROM articles WHERE title = %s", (article[0],))
                if cursor.fetchone()[0] == 0:
                    print(f"Inserting article: {article}")
                    cursor.execute(query, article)
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