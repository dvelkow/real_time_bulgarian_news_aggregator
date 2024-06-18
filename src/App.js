// src/App.js
import React from 'react';
import './App.css';
import NewsList from './components/NewsList';

function App() {
  return (
    <div className="App">
      <h1>Bulgarian News</h1>
      <NewsList />
    </div>
  );
}

export default App;
