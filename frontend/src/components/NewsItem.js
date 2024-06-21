import React from 'react';

const NewsItem = ({ article }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const options = { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: false,
      timeZone: 'Europe/Sofia'
    };
    return date.toLocaleString('en-GB', options);
  };

  return (
    <li className="news-item">
      <a href={article.link} target="_blank" rel="noopener noreferrer">
        {article.title}
      </a>
      <div className="news-item-meta">
        {formatDate(article.published)} - {article.source}
      </div>
    </li>
  );
};

export default NewsItem;