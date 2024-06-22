## Project Overview

This project is a real-time news aggregator for Bulgarian news sources, with a focus on implementing various data engineering skills.

 ![image](https://github.com/dvelkow/real_time_bulgarian_news_aggregator/assets/71397644/ec3bc194-926a-43e9-9473-4be8639ddb6c)

 
## Table of Contents
- [Key Components](#Key-Components)
- [Structure](#Structure)
- [Challenges and Learnings](#Challenges-and-Learnings)
- [Future Improvements](#Future-Improvements)

## Key Components

Here's where it gets interesting from a data engineering perspective:

1. **ETL Pipeline**: Set up a full Extract, Transform, Load pipeline utalizing Python, SQL and Pyspark. Data is extracted from web sources, transformed, and loaded into the database.

2. **Big Data Processing**: Utalized PySpark for data processing. Although this might be considered an overkill for our current data volume, it makes so the project can easily scale in the future and handle larger batches of data.

3. **Data Quality**: Data quality is ensured by cleaning it up with Pyspark through removing special characters, normalizing source names, standardizing timestamps.

4. **Scalability**: The architecture is set up so it could easily scale. We can add considerably more news sources or increase scraping frequency, our PySpark processing can handle the load.

5. **Automation**: The app automatically fetches new news sources once every X minutes throught the scheduling python library (X is currently 10, but can be lowered so we can get even closer to real-time)

## Structure

### Backend
- Boots up the dashboard thorugh app.py
- Manages all database operations through fetch_news.py and process_news.py, ensuring data integrity and efficient querying
- Triggers scheduled news fetching processes via fetch_news.py, maintaining up-to-date content
  
### Frontend 
- Fetches data from the backend utalizing JavaScript 
- Displays the latest news articles in a user-friendly interface
- Implements client-side sorting and filtering of news articles for improved user experience
- Utilizes React components for a maintainable code structure

## Challenges and Learnings

Some of the hurdles I stumbled upon while building it:

- Web scraping is rather needy. All news sites have different HTML structures, meaning the fetch function needed to be rewritten for every different site, some were trickier then others. 
- Balancing between real-time news aggregation and not filling all the slots of the site with spam news, as the sites some times tend to post multiple small news one after another.
- Setting up PySpark locally proved to be... painful.


## Future Improvements

There's always room for more:

- Implement real-time processing with Spark Streaming
- Add sentiment analysis of news headlines
- Set up a proper data warehouse for long-term analytics
- Containerize the whole setup with Docker for easier deployment

## Final Thoughts

This project has been a great way to get hands-on experience with various data engineering tools and techniques. It's one thing to read about these concepts, but actually implementing them and during the process it felt that's where the real learning happend.

Feel free to fork, improve, or completely overhaul this project. And if you're from one of the news sites we're scraping - um, please don't change your HTML structure? Thanks!
