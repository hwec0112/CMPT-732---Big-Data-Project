import sys
assert sys.version_info >= (3, 5)  # make sure we have Python 3.5+
from pyspark.sql import SparkSession, types, Window
from pyspark.sql.functions import rank, col, to_timestamp, year, month, explode, broadcast, avg, count, sum, lit, when
from pyspark.sql import functions

def main():
    input_dir = "../Processed_Data"
    output_dir = "../web_dev/apps/analysis_data"

    #Read movie data
    movie_df = spark.read.parquet(input_dir+"/movies_aggregated_data.parquet")
    #variable made by Tavleen for analysis
    movie_data = movie_df

    #populate average for Null values so that these values dont effect analysis
    profit_avg = int(movie_data.where(movie_data['profit'].isNotNull()).select(movie_data['*'], lit(1).alias('dummy'))\
                    .groupBy('dummy').agg(avg(movie_data['profit']).alias('avg_profit')).rdd.collect()[0].avg_profit)
    #print(profit_avg)
    popularity_avg = int(movie_data.where(movie_data['popularity'].isNotNull()).select(movie_data['*'], lit(1).alias('dummy'))\
                    .groupBy('dummy').agg(avg(movie_data['popularity']).alias('avg_pop')).rdd.collect()[0].avg_pop)
    #print(popularity_avg)
    avg_user_rating_avg = int(movie_data.where(movie_data['avg_user_rating'].isNotNull()).select(movie_data['*'], lit(1).alias('dummy'))\
                    .groupBy('dummy').agg(avg(movie_data['avg_user_rating']).alias('avg_user')).rdd.collect()[0].avg_user)
    #print(avg_user_rating_avg)
    vote_avg_avg = int(movie_data.where(movie_data['vote_average'].isNotNull()).select(movie_data['*'], lit(1).alias('dummy'))\
                    .groupBy('dummy').agg(avg(movie_data['vote_average']).alias('avg_vote')).rdd.collect()[0].avg_vote)
    #print(vote_avg_avg)
    movie_data_avg = movie_data.withColumn("profit_new", when(movie_data['profit'].isNull(), profit_avg).otherwise(movie_data['profit']))\
                                .drop("profit").withColumnRenamed("profit_new", "profit") \
                                .withColumn("popularity_new", when(movie_data['popularity'].isNull(), popularity_avg).otherwise(movie_data['popularity']))\
                                .drop("popularity").withColumnRenamed("popularity_new", "popularity") \
                                .withColumn("avg_user_rating_new", when(movie_data['avg_user_rating'].isNull(), avg_user_rating_avg).otherwise(movie_data['avg_user_rating']))\
                                .drop("avg_user_rating").withColumnRenamed("avg_user_rating_new", "avg_user_rating") \
                                .withColumn("vote_average_new", when(movie_data['vote_average'].isNull(), vote_avg_avg).otherwise(movie_data['vote_average']))\
                                .drop("vote_average").withColumnRenamed("vote_average_new", "vote_average") 
    print(movie_data_avg.where(movie_data['profit'].isNotNull() & movie_data['profit'].isNotNull() & movie_data['profit'].isNotNull() & movie_data['profit'].isNotNull()).count())
    
    #movie_data_avg.show(10)

    #movie_df.describe('popularity').show()
    #movie_df.describe('vote_average').show()
    #movie_df.show(1)
    movie_df.printSchema()
    #print(movie_df.count())
    #drop rows contain null
    movie_df = movie_df.na.drop(subset=["title", 'release_date', "popularity", "profit", 'avg_user_rating', 'vote_average'])
    #create new columns for processing
    movie_df = movie_df.withColumn('year', year(to_timestamp(movie_df['release_date'], 'yyyy-MM-dd')))
    movie_df = movie_df.withColumn('month', month(to_timestamp(movie_df['release_date'], 'yyyy-MM-dd')))
    #movie_df.where(col('title') == "The Guide").show()
    #movie_df = movie_df.dropDuplicates()
    cached_movie_df = movie_df.cache()

    #******Read genre_data******
    genre_df = spark.read.parquet(input_dir+"/genre_details.parquet")
    #drop genres that's not in the list since the amount of data is not enough for analysis
    #genres_list = ['Drama', 'Comedy', 'Thriller', 'Romance', 'Action', 'Horror', 'Crime', 'Adventure', 'Science Fiction', 'Mystery', 'Fantasy', 'Animation']
    #genre_df = genre_df.where(genre_df['genre_name'].isin(genres_list))

    #******Read production company detail data******
    company_df = spark.read.parquet(input_dir+"/company_details.parquet")
    #company_df.show(10)

    #******Read collection detail data******
    collection_df = spark.read.parquet(input_dir+"/collection_details.parquet").select(col('collection_ids').alias('collection_id'), 'collection_name')
    #collection_df.show(10)
    
    #******Read keyword detail data******
    keyword_df = spark.read.parquet(input_dir+"/keyword_details.parquet")
    #collection_df.show(10)
    
    #******task1 10 Most popular/highest return/highest avg user-rated/highest vote average movies each year (2000-2017)******
    task1_df = cached_movie_df.select("title", 'profit', "vote_average", "popularity", 'avg_user_rating', "year")
    task1_df = task1_df.where((task1_df['year'] >= 2000) & (task1_df['year'] <= 2017))
    #use windows to partition and sort data
    popularity_window = Window.partitionBy('year').orderBy(col('popularity').desc())
    vote_average_window = Window.partitionBy('year').orderBy(col('vote_average').desc())
    profit_window = Window.partitionBy('year').orderBy(col('profit').desc())
    avg_user_rating_window = Window.partitionBy('year').orderBy(col('avg_user_rating').desc())

    #call window and create new ranking columns
    task1_df = task1_df.select('*', rank().over(popularity_window).alias('poularity_rank'))
    task1_df = task1_df.select('*', rank().over(vote_average_window).alias('vote_average_rank'))
    task1_df = task1_df.select('*', rank().over(profit_window).alias('profit_rank'))
    task1_df = task1_df.select('*', rank().over(profit_window).alias('avg_user_rating_rank'))
    task1_df = task1_df.where((col('poularity_rank') <= 10) | (col('vote_average_rank') <= 10) | (col('profit_rank') <= 10) | (col('avg_user_rating_rank') <= 10))
    #drop unused columns
    task1_df = task1_df.drop('poularity_rank', 'vote_average_rank', 'profit_rank', 'avg_user_rating_rank')
    #task1_df.where(col('title') == "The Guide").show()
    # print('task1 result')
    # task1_df.show(10)
    #task1_df.write.mode('overwrite').parquet(output_dir + "/task1")

    #******create genre x movie data ******
    ex_movie_df = cached_movie_df.select('*', explode(cached_movie_df['genre_ids']).alias('genre_id'))
    ex_movie_df = ex_movie_df.drop('genre_ids', 'month')
    genre_movie_df = ex_movie_df.join(broadcast(genre_df), 'genre_id')
    genre_movie_df = genre_movie_df.cache()

    #***task2 10 Most popular/highest return/highest avg rated/highest vote average genre each year (2000-2017)******
    task2_df = genre_movie_df.select('profit', "vote_average", "popularity", 'avg_user_rating', "year", 'genre_name')
    task2_df = task2_df.where((task2_df['year'] >= 2000) & (task2_df['year'] <= 2017))
    task2_df = genre_movie_df.groupBy('year','genre_name').agg(avg(col('profit')).alias('profit'), avg(col('popularity')).alias('popularity'), avg(col('vote_average')).alias('vote_average'), avg(col('avg_user_rating')).alias('avg_user_rating'))
    # print('task2 result')
    # task2_df.show(10)
    #task2_df.write.mode('overwrite').parquet(output_dir + "/task2")

    #******genre analysis task3 10 Most popular/highest return/highest avg rated/highest vote average movie in each genre (2000-2017)******
    #genre_movie_df.show(20)
    task3_df = genre_movie_df.select("year", 'genre_name', 'title', 'profit', "vote_average", "popularity", 'avg_user_rating')
    task3_df = task3_df.where((task3_df['year'] >= 2000) & (task3_df['year'] <= 2017))
    genre_pop_window = Window.partitionBy('genre_name').orderBy(col('popularity').desc())
    genre_profit_window = Window.partitionBy('genre_name').orderBy(col('profit').desc())
    genre_vote_average_window = Window.partitionBy('genre_name').orderBy(col('vote_average').desc())
    genre_avg_user_rating_window = Window.partitionBy('genre_name').orderBy(col('avg_user_rating').desc())

    task3_df = task3_df.select('*', rank().over(genre_pop_window).alias('poularity_rank'))
    task3_df = task3_df.select('*', rank().over(genre_profit_window).alias('profit_rank'))
    task3_df = task3_df.select('*', rank().over(genre_vote_average_window).alias('vote_average_rank'))
    task3_df = task3_df.select('*', rank().over(genre_avg_user_rating_window).alias('avg_user_rating_rank'))
    task3_df = task3_df.where((col('poularity_rank') <= 10) | (col('vote_average_rank') <= 10) | (col('profit_rank') <= 10) | (col('avg_user_rating_rank') <= 10))
    task3_df = task3_df.drop('poularity_rank', 'vote_average_rank', 'profit_rank', 'avg_user_rating_rank')
    # print('task3 result')
    # task3_df.show(10)
    #task3_df.write.mode('overwrite').parquet(output_dir + "/task3")
    
    #******task4 Top 10 Prod companies with movies that are Most(or avg?) popular/highest avg profit/highest avg rated/highest vote average (all-time)******
    task4_df = cached_movie_df.select('profit', "vote_average", "popularity", 'avg_user_rating', 'production_company_ids')
    task4_df = task4_df.select('*', explode(task4_df['production_company_ids']).alias('company_id')).drop('production_company_ids')
    task4_df = task4_df.join(broadcast(company_df), 'company_id')
    task4_df = task4_df.groupBy('production_company').agg(count(col('profit')).alias('count'), avg(col('profit')).alias('profit'), avg(col('popularity')).alias('popularity'), avg(col('vote_average')).alias('vote_average'), avg(col('avg_user_rating')).alias('avg_user_rating'))
    task4_df = task4_df.where(task4_df['count'] > 15).drop('count')
    #print(task4_df.count())
    #task4_df.orderBy(task4_df['profit'], ascending = False).show(10)
    #task4_df.write.mode('overwrite').parquet(output_dir + "/task4")

    #******task8 Original languages other than english which have highest avg popularity, max total revenue, highest average ratings******
    task8_df = cached_movie_df.select('profit', "vote_average", "popularity", 'avg_user_rating', 'language_id')
    task8_df = task8_df.select('*', explode(task8_df['language_id']).alias('language')).drop('language_id')
    task8_df = task8_df.groupBy('language').agg(count(col('profit')).alias('count'), avg(col('profit')).alias('profit'), avg(col('popularity')).alias('popularity'), avg(col('vote_average')).alias('vote_average'), avg(col('avg_user_rating')).alias('avg_user_rating'))
    task8_df = task8_df.where(task8_df['count'] > 50)
    #print(task8_df.count())
    #task8_df.show(20)
    #task8_df.write.mode('overwrite').parquet(output_dir + "/task8")

    #******task11 Collection with movies of highest avg popularity, highest return, highest avg return and highest avg rating******
    task11_df = cached_movie_df.select('profit', "vote_average", "popularity", 'avg_user_rating', 'collection_ids')
    task11_df = task11_df.select('*', explode(task11_df['collection_ids']).alias('collection_id')).drop('collection_ids')
    #No big difference in join
    task11_df = task11_df.join(collection_df, 'collection_id')
    task11_df = task11_df.groupBy('collection_name').agg(count(col('profit')).alias('count'), avg(col('profit')).alias('profit'), avg(col('popularity')).alias('popularity'), avg(col('vote_average')).alias('vote_average'), avg(col('avg_user_rating')).alias('avg_user_rating'))
    task11_df = task11_df.where(task11_df['count'] > 1)
    #print(task11_df.count())
    #task11_df.show(20)
    #task11_df.write.mode('overwrite').parquet(output_dir + "/task11")
    
    #******task6 Most common words in movie titles******
    #Insight: Were the most frequent choice of words for a movie title. A carefully chosen and intruiging title can boost box office sales and popularity a movie. Therefore, the most frequent choice may be worth noting '''
    task6_df = movie_data.select(functions.explode(functions.split(movie_data['title'], " ")).alias('title'))
    task6_df.show(20)
    #task6_df.write.mode('overwrite').parquet(output_dir + "/task6")

    #******task7 Most common themes in movies******
    #Insight: "Woman director", "independent film", and "murder" are the most frequent keywords used to tag movies. This gives us insight into themes that the creators or the public believe are important features and can promote a movie's success
    task7_df = movie_data.select(movie_data['keyword_ids'])
    task7_df = task7_df.select(explode(task7_df['keyword_ids']).alias('keyword_id')) 
    #task7_df = task7_df.groupBy('keyword_id').agg(count(task7_df['dummy']).alias('count'))
    task7_df = task7_df.join(keyword_df, keyword_df['keyword_id']==task7_df['keyword_id']).select(keyword_df['keyword'])
    #task7_df.write.mode('overwrite').parquet(output_dir + "/task7")

    #******task14 Most common release month + release months that generate the highest avg return******
    #Display % of movies released each month as pie chart and month-avg profit as horizontal bar graph
    task14_df = cached_movie_df.groupBy("month").agg(count(cached_movie_df['tmdb_id']).alias('count'), avg(cached_movie_df['profit']).alias('avg_profit'))
    task14_df.show(12)
    #task14_df.write.mode('overwrite').parquet(output_dir + "/task14")

    '''#******Correlation of popularity/highest return/highest avg user-rated/highest vote average with ******
    task15_df = movie_data.na.drop.select(budget, popularity, revenue, vote_average, vote_count, runtime,avg_user_rating)
    task15_df = cached_movie_df.groupBy("month").agg(count(cached_movie_df['tmdb_id']).alias('count'), sum(cached_movie_df['profit']).alias('sum'))
    task15_df.show(12)
    #task15_df.write.mode('overwrite').parquet(output_dir + "/task15")'''

if __name__ == '__main__':
    spark = SparkSession.builder.appName("task1-3").getOrCreate()
    assert spark.version >= "2.4"  # make sure we have Spark 2.4+
    spark.sparkContext.setLogLevel("WARN")
    sc = spark.sparkContext
    main()