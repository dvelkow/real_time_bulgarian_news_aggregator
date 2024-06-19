import React, { useEffect, useState } from 'react';
import axios from 'axios';
import NewsItem from './NewsItem';

const NewsList = () => {
  const [articles, setArticles] = useState([]);

  useEffect(() => {
    const fetchArticles = async () => {
      try {
        const response = await axios.get('http://localhost:5000/news');
        setArticles(response.data);
      } catch (error) {
        console.error('Error fetching articles:', error);
      }
    };

    fetchArticles();
  }, []);

  return (
    <ul className="news-list">
      {articles.map(article => (
        <NewsItem key={article.id} article={article} />
      ))}
    </ul>
  );
};

export default NewsList;
