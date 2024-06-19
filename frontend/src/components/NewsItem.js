import React from 'react';

const NewsItem = ({ article }) => (
  <li>
    <a href={article.link} target="_blank" rel="noopener noreferrer">
      {article.title}
    </a> - {new Date(article.published).toLocaleString()}
  </li>
);

export default NewsItem;
