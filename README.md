## Project Overview

This project is a real-time news aggregator for Bulgarian news sources, with a focus on implementing various data engineering skills.

<img src="https://github.com/dvelkow/real_time_bulgarian_news_aggregator/assets/71397644/5a858c6e-4688-4ee8-a086-0b36ee0b6b94" alt="image" width="800"/>

 
## Table of Contents
- [Key Components](#Key-Components)
- [Key Functionalities](#Key-Functionalities)
- [Challenges and Learnings](#Challenges-and-Learnings)
- [Future Improvements](#Future-Improvements)
- [Setup Instructions](#Setup-Instructions)

## Key Components

Here's where it gets interesting from a data engineering perspective:

1. **ETL Pipeline**: Set up a full Extract, Transform, Load pipeline utalizing Python, SQL and Pyspark. Data is extracted from web sources, transformed, and loaded into the database.

2. **Big Data Processing**: Utalized PySpark for data processing. Although this might be considered an overkill for our current data volume, it makes so the project can easily scale in the future and handle larger batches of data.

3. **Data Quality**: Data quality is ensured by cleaning it up with Pyspark through removing special characters, normalizing source names, standardizing timestamps.

4. **Scalability**: The architecture is set up so it could easily scale. We can add considerably more news sources or increase scraping frequency, our PySpark processing can handle the load.

5. **Automation**: The app automatically fetches new news sources once every X minutes throught the scheduling python library (X is currently 10, but can be lowered so we can get even closer to real-time)


## Key Functionalities

- Aggregates news from multiple Bulgarian news sources including 24chasa, Dnevnik, and Fakti
- Provides direct links to original news articles for further reading
- Automatically updates the news database at regular intervals to ensure fresh content
- Offers a simple and intuitive user interface for browsing the latest news

## Setup

1. **Clone the repository**:

    ```sh
    git clone https://github.com/dvelkow/real_time_bulgarian_news_aggregator.git
    cd real_time_bulgarian_news_aggregator/backend
    ```

2. **install dependencies**:

    ```sh
    pip install -r requirements.txt
    ```

3. **Create a `.env` file in the main directory and add your MySQL credentials, u need to have a**:

    ```env
    DB_HOST=localhost
    DB_NAME= db_news /needs to be created first in MYSQL 
    DB_USER= root
    DB_PASSWORD=your_mysql_password
    ```

4. **Run the Flask application**:

    ```sh
    python app.py
    ```

## Challenges and Learnings

Some of the hurdles I stumbled upon while building it:

- Web scraping is rather needy. All news sites have different HTML structures, meaning the fetch function needed to be rewritten for every different site, some were trickier then others. 
- Balancing between real-time news aggregation and not filling all the slots of the site with spam news, as the sites sometimes tend to post multiple small news one after another.
- Setting up PySpark locally proved to be... painful.


## Future Improvements

There's always room for more:

- Adding different tags based on news headlines and making topics on the site
- Having an option for seeing trending news, could be done by taking the averages of the sites for views/hour and if a news article is beating it substantially we could determine it's trending

I might work on these changes in the future but seeing as they are not closely related to data engineering I would no be implementing them now, as my focus is elsewhere. 

## Final Thoughts

This project has been a great way to get hands-on experience with various data engineering tools and techniques I have only read/watched about. It's one thing to read about these concepts, but actually implementing them and during the process it felt that's where the real learning happend.
