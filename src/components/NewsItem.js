// src/components/NewsItem.js
import React from 'react';

const NewsItem = ({ title, link }) => (
  <li className="news-item">
    <a href={link} className="news-link" target="_blank" rel="noopener noreferrer">
      {title}
    </a>
  </li>
);

export default NewsItem;
