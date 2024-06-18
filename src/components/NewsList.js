// src/components/NewsList.js
import React from 'react';
import NewsItem from './NewsItem';

const NewsList = () => {
  const placeholders = [
    { id: 1, title: 'Placeholder News 1', link: '#' },
    { id: 2, title: 'Placeholder News 2', link: '#' },
    { id: 3, title: 'Placeholder News 3', link: '#' },
    { id: 4, title: 'Placeholder News 4', link: '#' },
    { id: 5, title: 'Placeholder News 5', link: '#' },
    { id: 6, title: 'Placeholder News 6', link: '#' },
    { id: 7, title: 'Placeholder News 7', link: '#' },
    { id: 8, title: 'Placeholder News 8', link: '#' },
    { id: 9, title: 'Placeholder News 9', link: '#' },
    { id: 10, title: 'Placeholder News 10', link: '#' },
  ];

  return (
    <ul className="news-list">
      {placeholders.map(item => (
        <NewsItem key={item.id} title={item.title} link={item.link} />
      ))}
    </ul>
  );
};

export default NewsList;
