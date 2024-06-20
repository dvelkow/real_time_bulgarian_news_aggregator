import React from 'react';
import './App.css';
import NewsList from './components/NewsList';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Latest News in Bulgaria</h1>
      </header>
      <NewsList />
    </div>
  );
}

export default App;
