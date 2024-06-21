import React, { useEffect, useState } from 'react';
import axios from 'axios';
import NewsItem from './NewsItem';

const NewsList = () => {
  const [articles, setArticles] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchArticles = async () => {
      try {
        const response = await axios.get('/news');
        console.log('API response:', response.data); // For debugging
        if (Array.isArray(response.data)) {
          setArticles(response.data);
        } else if (response.data && Array.isArray(response.data.articles)) {
          setArticles(response.data.articles);
        } else {
          throw new Error('Unexpected data format');
        }
        setLoading(false);
      } catch (error) {
        console.error('Error fetching articles:', error);
        setError('Failed to fetch articles. Please try again later.');
        setLoading(false);
      }
    };

    fetchArticles();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <ul className="news-list">
      {articles.length > 0 ? (
        articles.map((article) => (
          <NewsItem key={article.id} article={article} />
        ))
      ) : (
        <li>No articles found</li>
      )}
    </ul>
  );
};

export default NewsList;