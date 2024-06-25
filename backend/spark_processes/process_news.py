from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, date_format, to_date, year, month, dayofmonth, hour, desc
from pyspark.sql.types import StructType, StructField, StringType, TimestampType
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def create_spark_session():
    return SparkSession.builder \
        .appName("NewsDataProcessor") \
        .config("spark.jars", "/path/to/mysql-connector-java.jar") \
        .getOrCreate()

def load_data_from_mysql(spark):
    jdbc_url = f"jdbc:mysql://{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    return spark.read \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", "articles") \
        .option("user", os.getenv('DB_USER')) \
        .option("password", os.getenv('DB_PASSWORD')) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .load()

def process_news_data(df):
    # Count articles by source
    source_counts = df.groupBy("source").count().orderBy(desc("count"))
    # Count articles by date
    df = df.withColumn("date", to_date(col("published")))
    date_counts = df.groupBy("date").count().orderBy("date")
    # Count articles by hour of day
    hour_counts = df.withColumn("hour", hour(col("published"))) \
        .groupBy("hour") \
        .count() \
        .orderBy("hour")
    # Top 10 days with most articles
    top_days = date_counts.orderBy(desc("count")).limit(10)
    return source_counts, date_counts, hour_counts, top_days

def create_new_database():
    connection = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    cursor = connection.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS processed_news_db")
    cursor.close()
    connection.close()

def save_to_mysql(df, table_name):
    jdbc_url = f"jdbc:mysql://{os.getenv('DB_HOST')}/processed_news_db"
    df.write \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", table_name) \
        .option("user", os.getenv('DB_USER')) \
        .option("password", os.getenv('DB_PASSWORD')) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .mode("overwrite") \
        .save()

def main():
    create_new_database()
    spark = create_spark_session()
    # Load data
    df = load_data_from_mysql(spark)
    # Process data
    source_counts, date_counts, hour_counts, top_days = process_news_data(df)
    # Save processed data
    save_to_mysql(source_counts, "news_source_counts")
    save_to_mysql(date_counts, "news_date_counts")
    save_to_mysql(hour_counts, "news_hour_counts")
    save_to_mysql(top_days, "news_top_days")
    spark.stop()

if __name__ == "__main__":
    main()