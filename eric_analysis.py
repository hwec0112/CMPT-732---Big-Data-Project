import sys
assert sys.version_info >= (3, 5)  # make sure we have Python 3.5+
from pyspark.sql import SparkSession, types, Window
from pyspark.sql.functions import rank, col, to_timestamp, year, month, explode

def main(movie_path, genre_path):
    output_dir = "analysis_data"
    movie_data = spark.read.parquet(movie_path)
    #movie_data.describe('popularity').show()
    #movie_data.describe('vote_average').show()
    #remove null data slot
    movie_data = movie_data.na.drop(subset=["title", "release_date", "popularity", "genre_ids", "budget", "profit"])
    #create new columns for processing
    movie_data = movie_data.select((movie_data["profit"]/movie_data["budget"]).alias("return") , movie_data["genre_ids"], movie_data["vote_average"], movie_data["title"], movie_data["popularity"], movie_data["release_date"])
    movie_data = movie_data.withColumn('year', year(to_timestamp(movie_data['release_date'], 'yyyy-MM-dd')))
    movie_data = movie_data.withColumn('month', month(to_timestamp(movie_data['release_date'], 'yyyy-MM-dd')))
    movie_data = movie_data.where((movie_data['year'] > 2007) & (movie_data['year'] <= 2017)).drop("release_date")
    cached_movie_data = movie_data.cache()
    #use windows to partition and sort data
    popularity_window = Window.partitionBy(cached_movie_data['year']).orderBy(cached_movie_data['popularity'].desc())
    vote_average_window = Window.partitionBy(cached_movie_data['year']).orderBy(cached_movie_data['vote_average'].desc())
    return_window = Window.partitionBy(cached_movie_data['year']).orderBy(cached_movie_data['return'].desc())
    # #call window and create new ranking columns
    # year_return_data = cached_movie_data.drop('month')
    # year_return_data = year_return_data.select('*', rank().over(popularity_window).alias('poularity_rank'))
    # year_return_data = year_return_data.select('*', rank().over(vote_average_window).alias('vote_average_rank'))
    # year_return_data = year_return_data.select('*', rank().over(return_window).alias('return_rank'))
    # year_return_data = year_return_data.where((col('poularity_rank') <= 10) | (col('vote_average_rank') <= 10) | (col('return_rank') <= 10))
    # #drop unused columns
    # year_return_data = year_return_data.drop('poularity_rank', 'vote_average_rank', 'return_rank')
    # print(year_return_data.count())
    # year_return_data.show(10)
    # year_return_data.write.mode('overwrite').parquet(output_dir + "/year_return")

    #genre analysis
    genre_data = spark.read.parquet(genre_path)
    genre_data.orderBy(genre_data['genre_id'].desc()).show(50)
    #drop genres that's not in the list since the amount of data is not enough for analysis
    #genres_list = ['Drama', 'Comedy', 'Thriller', 'Romance', 'Action', 'Horror', 'Crime', 'Adventure', 'Science Fiction', 'Mystery', 'Fantasy', 'Animation']
    #genre_data = genre_data.where(genre_data['genre_name'].isin(genres_list))
    genre_data.show(12)
    ex_movie_data = cached_movie_data.select('*', explode(cached_movie_data['genre_ids']).alias('genre_id'))
    ex_movie_data = ex_movie_data.drop('genre_ids', 'month')
    genre_movie_data = ex_movie_data.join(genre_data, 'genre_id')
    genre_movie_data.show(20)
    #genre_movie_data = genre_movie_data.groupBy('genre_id').count().orderBy('count')
    #genre_movie_data = genre_movie_data.groupBy('genre_id').agg({''})

if __name__ == '__main__':
    movie_path = sys.argv[1]
    genre_path = sys.argv[2]
    spark = SparkSession.builder.appName("temporal_trend_analysis").getOrCreate()
    assert spark.version >= "2.4"  # make sure we have Spark 2.4+
    spark.sparkContext.setLogLevel("WARN")
    sc = spark.sparkContext
    main(movie_path, genre_path)