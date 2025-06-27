from pyspark.sql.functions import date_format, col, to_timestamp, coalesce, udf, struct,  lit, when, row_number
import datetime, requests, subprocess, argparse
import json, time, traceback, logging, random
from newspaper import Article, Config
from pyspark.sql.window import Window
from pyspark.sql import SparkSession
from multiprocessing.pool import Pool

site='20min'

FEEDS_RSS = [
    ('20Min home', u'https://www.20minutos.es/rss')
]

SITEMAP = [
    ('20Min', u'https://www.20minutos.es/sitemap-google-news.xml')
]

# Settings Newspaper, Spark Configuration, Argparse
user_agents = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'
]

def get_data(link):
    attempt = 4
    retry_delay = 10
    retry = True
    while retry and attempt > 0:
        try:
            user_agent = random.choice(user_agents)
            config = Config()
            config.browser_user_agent = user_agent
            config.request_timeout = 120
            article = Article(link, config=config, headers={'User-Agent': random.choice(user_agents)})
            article.download()
            article.parse()
            article_dict = article.extractor.get_meta_data(article.clean_doc)
            article_dict['html'] = article.html
            article_dict['testo'] = article.text
            article_json = json.dumps(article_dict, indent = 4)
            return article_json
        except Exception:
            if '403' in traceback.format_exc():
                logging.warn('***FAILED TO DOWNLOAD***', article.url)
                time.sleep(retry_delay)
                retry_delay = retry_delay + 10
            else:
                attempt = attempt - 1
                if attempt == 0:
                    return """'("error_url_report": "{}", "error_execution_real_time": "{}")""".format(article.url, traceback.format_exc())
                else:
                    time.sleep(retry_delay)
                    retry_delay = retry_delay + 10
                    logging.warn('***FAILED TO DOWNLOAD***', traceback.format_exc())

def get_last_mod(row):
    link = row["loc"]
    data = get_data(link)
    if "error_url_report" not in data:
        data = json.loads(data)
        modified_time = None
        article = data.get("article")
        if article is not None:
            modified_time = article.get("modified_time")
        else:
            article = data.get("og")
            if article is not None:
                modified_time = article.get("modified_time")
        return modified_time

# Registry udf function
def get_article(row) -> str:
    link = row['link']
    return get_data(link)

def get_day_in_italian(row) -> str:
    day = row['day_of_week']
    days = {'Monday': 'Lunedì', 'Tuesday': 'Martedì', 'Wednesday': 'Mercoledì',
            'Thursday': 'Giovedì', 'Friday': 'Venerdì', 'Saturday': 'Sabato', 'Sunday': 'Domenica'}
    return days.get(day, 'Invalid day')

def parse_article(column, row) -> str:
    data = row['data']
    if data is not None:
        data = json.loads(row['data'])
        columns = column.split('.')
        for c in columns:
            if data is not None:
                data = data.get(c)
        return data

def get_category(row) -> str:
    url = row['og.url']
    if 'https://video.repubblica.it' in url:
        return 'video'
    else:
        url_splitted = row['og.url'].split('/')
        category = url_splitted[3]
        if category == 'pwa':
            category = url_splitted[4]
        return category

    
#nota DC: get_edition va rifatto a seconda delle necessità spagnole
def get_edition(row):
    url = row['og.url']
    return "Undefined"


get_last_mod_udf = udf(lambda row: get_last_mod(row))
get_article_udf = udf(lambda row: get_article(row))
parse_article_udf = udf(lambda column, row: parse_article(column, row))
get_category_udf = udf(lambda row: get_category(row))
get_edition_udf = udf(lambda row: get_edition(row))
#get_day_in_italian_udf = udf(lambda row: get_day_in_italian(row))

# Repubblica near real time.
CLI=argparse.ArgumentParser()

CLI.add_argument(
    "--fec_datos",
    type=str,
    required=True
)

CLI.add_argument(
    "--hour",
    type=str,
    required=True
)

CLI.add_argument(
    "--delay",
    type=str,
    required=True
)

CLI.add_argument(
    "--env",
    type=str,
    required=True
)

#hour=int('18')
#fec_datos='2023-06-21'
#date = datetime.datetime.strptime(fec_datos + f":{hour}", "%Y-%m-%d:%H")
#year=int('2023')
#month=int('06')
#day=int('21')
#delay = int('15')
#env='dev'
#date_start = (date - datetime.timedelta(hours=int(delay)))


args = CLI.parse_args()
hour = args.hour
date = datetime.datetime.strptime(args.fec_datos + f":{hour}", "%Y-%m-%d:%H")
year = date.year
month = date.month
day = date.day
delay = args.delay
env = args.env
date_start = (date - datetime.timedelta(hours=int(delay)))

if env.lower() == 'prod':
    bucket_raw = "ueproetl-data/raw_data"
    bucket_curated = "ueproetl-data/curated_data"
    bucket_published = "ueproetl-data/published_data/generic"
#elif env.lower() == 'preprod':
#    bucket_raw = "rcs-pre-data/raw_data"
#    bucket_curated = "rcs-pre-data/curated_data"
#    bucket_published = "rcs-pre-data/published_data/generic"
elif env.lower() == 'dev':
    bucket_raw = "uestaetldtp21-hive/tmp/scraper_test/raw_data"
    bucket_curated = "uestaetldtp21-hive/tmp/scraper_test/curated_data"
    bucket_published = "uestaetldtp21-hive/tmp/scraper_test/published_data"
else:
    raise Exception(f"Error the env provided is not valid (prod, preprod, dev): {env.lower()}")

# Registry utility function
def write_df_from_addrs(df, addrs, flow_id):
    print(f"__INFO__ : PHASE {flow_id} START")
    if flow_id == 'feed_rss':
        df = df.withColumn("year", date_format(coalesce(to_timestamp(col("pubDate"), "EEE, dd MMM yyyy HH:mm:ss Z"),to_timestamp(col("pubDate"))), "yyyy"))
        df = df.withColumn("month", date_format(coalesce(to_timestamp(col("pubDate"), "EEE, dd MMM yyyy HH:mm:ss Z"),to_timestamp(col("pubDate"))), "MM"))
        df = df.withColumn("day", date_format(coalesce(to_timestamp(col("pubDate"), "EEE, dd MMM yyyy HH:mm:ss Z"),to_timestamp(col("pubDate"))), "dd"))
        df = df.withColumn("hour", date_format(coalesce(to_timestamp(col("pubDate"), "EEE, dd MMM yyyy HH:mm:ss Z"),to_timestamp(col("pubDate"))), "HH"))
        print("test DC")
        df.printSchema()
    elif flow_id == 'sitemap':
        df_tmp = df.filter("lastmod is null").filter((col("news:news.news:publication_date") < "%d-%02d-%02d %02d:00:00" % (date.year,date.month,date.day, date.hour+1)))
        df_tmp = df_tmp.withColumn("lastmod", get_last_mod_udf(struct(df['loc']))).cache()
        df_tmp.createOrReplaceTempView("df_tmp")
        df = df.filter("lastmod is not null")
        df.createOrReplaceTempView("df")
        df = spark.sql("select * from df union all select * from df_tmp")
        df = df.withColumn("lastmod", coalesce(col("lastmod"), col("news:news.news:publication_date")))
        df = df.withColumn("year", date_format(col('lastmod'), "yyyy"))
        df = df.withColumn("month", date_format(col('lastmod'), "MM"))
        df = df.withColumn("day", date_format(col('lastmod'), "dd"))
        df = df.withColumn("hour", date_format(col('lastmod'), "HH"))
    else:
        raise Exception("Error flow_id")

    df =  df.filter("int(concat(year,month,day,hour)) >= %d%02d%02d%02d" % (date_start.year,date_start.month,date_start.day, date_start.hour)). \
        filter("int(concat(year,month,day,hour)) <= %d%02d%02d%02d" % (date.year,date.month,date.day, date.hour))
    addrs_filtered = []
    for add in addrs:
        try:
            spark.read.parquet(add)
            addrs_filtered.append(add)
        except:
            print("Not found " + add)
    try:
        print(addrs_filtered)
        df_old = spark.read.option("basePath", f"gs://{bucket_curated}/{site}/{flow_id}").parquet(*addrs_filtered)
    except:
        df.write.partitionBy('year', 'month', 'day', 'hour').parquet(f"gs://{bucket_curated}/{site}/{flow_id}", mode="overwrite")
        print(f"__INFO__ : PHASE {flow_id} END")
    else:
        print("__INFO__SCHEMA CHECK....")
        print(df.columns)
        print(df_old.columns)
        assert df.columns == df_old.columns
        print("__INFO__SCHEMA CHECK END....")
        result = df.union(df_old)
        result = result.dropDuplicates()
        result.show()
        result.write.partitionBy('year', 'month', 'day', 'hour').parquet(f"gs://{bucket_curated}/{site}/{flow_id}", mode="overwrite")
        print(f"__INFO__ : PHASE {flow_id} END")

# Spark create Session
spark = SparkSession.builder. \
    config("spark.sql.sources.partitionOverwriteMode", "dynamic"). \
    config("spark.jars.packages", "com.databricks:spark-xml_2.12:0.16.0"). \
    config("spark.sql.sources.partitionColumnTypeInference.enabled", "false"). \
    config("spark.sql.legacy.timeParserPolicy", "LEGACY"). \
    config('spark.sql.session.timeZone', 'Europe/Rome'). \
    getOrCreate()

# -------------------------------- PHASE RAW 
""" - Info
In questa fase avviene lo scaricamento del dato,
c'è una file python di supporto (schema.py) dove all'interno troviamo due costanti
utili per lo scaricamento di tutti i feed rss esistenti attualmente per repubblica
per aggiungere un flusso semplicemente aggiungere un elemento nella lista (solo rssv2).
Il risultato dello scaricamento verrà storicizzato nel bucket in base all'ambiente
e partizionato per anno/mese/giorno/ora
"""
# Phase 1: Save History to Raw

def download_feed(feed):
    name, url = feed
    name = name.replace(" ", "").lower()
    print(f"__INFO__: Download {name} - url: {url}")
    retry = True
    retry_delay = 5
    while retry:
        r = requests.get(url)
        if r.status_code != 403:
            retry = False
        else:
            time.sleep(retry_delay)
            retry_delay = retry_delay + 5
    f = open(f"rss_{name}.xml", 'w')
    f.write(r.text)
    f.close()

def download_sitemap(sitemap):
    name_sitemap, url = sitemap
    retry = True
    retry_delay = 5
    while retry:
        if 'gz' in url:
            r = requests.get(url, stream=True, headers={'User-Agent': random.choice(user_agents)})
            mode = "wb"
            ext = '.gz'
        else:
            r = requests.get(url, headers={'User-Agent': random.choice(user_agents)})
            mode = "w"
            ext = ''
        if r.status_code != 403:
            retry = False
        else:
            time.sleep(retry_delay)
            retry_delay = retry_delay + 10
    f = open(f"{name_sitemap}.xml" + ext, mode)
    if ext != '':
        f.write(r.raw.read())
    else:
        f.write(r.text)
    f.close()

ts = time.time()
with Pool(4) as p:
    p.map(download_feed, FEEDS_RSS)
subprocess.check_call(
    f"gsutil -m mv rss_*.xml 'gs://{bucket_raw}/{site}/feed_rss/year=%d/month=%02d/day=%02d/hour=%02d/'" % (
        year, month, day, int(hour)), shell=True)
print('Took %s seconds', time.time() - ts)

print(f"__INFO__: Download Sitemap - url: {SITEMAP}")
ts = time.time()
with Pool(4) as p:
    p.map(download_sitemap, SITEMAP)
subprocess.check_call(
    f"gsutil -m mv *.xml* 'gs://{bucket_raw}/{site}/sitemap/year=%d/month=%02d/day=%02d/hour=%02d/'" % (
        year, month, day, int(hour)), shell=True)
print('Took %s seconds', time.time() - ts)
print(f"__INFO__: Download Sitemap done.")

#-------------------------------- PHASE RAW END

#-------------------------------- PHASE CURATED
""" - Info
In questa fase trasformiamo i files di partenza xml in un formato parquet aggiungendo 
anche colonne utili come anno/mese/giorno/ora di pubblicazione del file.
"""
# Phase 2: Save new data to Curated
addrs_feed_rss = [
    f'gs://{bucket_curated}/{site}/feed_rss/year=%d/month=%02d/day=%02d/hour=%02d/*'
    % (i.year, i.month, i.day, i.hour) for i in [(date - datetime.timedelta(hours=i + 1) ) for i in range(int(delay))]]

addrs_sitemap_rss = [
    f'gs://{bucket_curated}/{site}/sitemap/year=%d/month=%02d/day=%02d/hour=%02d/*'
    % (i.year, i.month, i.day, i.hour) for i in [(date - datetime.timedelta(hours=i + 1) ) for i in range(int(delay))]]

write_df_from_addrs(spark.read.option("mergeSchema", "true").format("xml").option("rowTag", "item").load(f'gs://{bucket_raw}/{site}/feed_rss' + '/year=%d/month=%02d/day=%02d/hour=%02d/' % (
    year, month, day, int(hour)) + '*.xml'), addrs_feed_rss, "feed_rss")

write_df_from_addrs(spark.read.option("mergeSchema", "true").format("xml").option("rowTag", "url").load(f'gs://{bucket_raw}/{site}/sitemap' + '/year=%d/month=%02d/day=%02d/hour=%02d/' % (
    year, month, day, int(hour)) + '*.xml*'), addrs_sitemap_rss, "sitemap")

# -------------------------------- PHASE CURATED END

# -------------------------------- PHASE PUBLISHED
""" - Info
In questa fase prendiamo in input lo strato curated e utilizziamo una finestra di {delay} 
per aggiornare gli articoli pubblicati, arricchendo la struttura di partenza con informazioni
aggiuntive.
"""


# Curated to Published RSS and SITEMAP
feed_rss = spark.read.parquet(f"gs://{bucket_curated}/{site}/feed_rss")
feed_rss.show(1,False)
sitemap = spark.read.parquet(f"gs://{bucket_curated}/{site}/sitemap")
sitemap.show(1,False)
feed_rss_clean = feed_rss.filter("int(concat(year,month,day,hour)) >= %d%02d%02d%02d" % (date_start.year,date_start.month,date_start.day, date_start.hour)). \
    filter("int(concat(year,month,day,hour)) <= %d%02d%02d%02d" % (date.year,date.month,date.day, date.hour)). \
    select('link', 'year', 'month', 'day', 'hour').drop_duplicates()
sitemap_clean = sitemap.filter("int(concat(year,month,day,hour)) >= %d%02d%02d%02d" % (date_start.year,date_start.month,date_start.day, date_start.hour)). \
    filter("int(concat(year,month,day,hour)) <= %d%02d%02d%02d" % (date.year,date.month,date.day, date.hour)). \
    select('loc', 'year', 'month', 'day', 'hour').drop_duplicates().withColumnRenamed("loc", "link")
union_feed_sitemap = feed_rss_clean.union(sitemap_clean).drop_duplicates()
union_feed_sitemap = union_feed_sitemap.withColumn("data", get_article_udf(struct([union_feed_sitemap[x] for x in union_feed_sitemap.columns]))).cache()

union_feed_sitemap = union_feed_sitemap.filter("data not like '%error_url_report%'").cache()
union_feed_sitemap_errors = union_feed_sitemap.filter("data like '%error_url_report%'")
union_feed_sitemap_errors.write.partitionBy("year", "month", "day", "hour").mode("append").parquet(f"gs://{bucket_published}/{site}_errors_report")

columns = ['description', 'keywords', 'news_keywords', 'tags', 'application-name',
           'image_thumb_src', 'thumb', 'viewport', 'format-detection', 'fb.app_id',
           'og.site_name', 'og.type', 'og.title', 'og.description', 'og.image',
           'og.url', 'article.publisher', 'article.published_time',
           'article.modified_time', 'article.content_tier', 'article.content_plan',
           'twitter.card', 'twitter.site', 'twitter.title', 'twitter.description',
           'twitter.image', 'twitter.url', 'gs.twitter.text', 'testo',
           'article.opening_media', 'msapplication-task', 'msapplication-tooltip',
           'msapplication-starturl', 'msapplication-window',
           'msapplication-TileColor', 'msapplication-TileImage', 'article.section',
           'robots', 'tbl.url', 'tbl.uid', 'og.published_time', 'og.modified_time',
           'og.section', 'ge.thumbnailurl', 'ge.fullframeurl', 'twitter.domain',
           'article.content_lab', 'html']

final_site = union_feed_sitemap

for column in columns:
    final_site = final_site.withColumn(f"{column}", parse_article_udf(lit(column), struct([union_feed_sitemap[x] for x in union_feed_sitemap.columns])))

final_site = final_site.drop("data").drop("link").drop_duplicates().cache()

final_site = final_site.filter("`og.url` is not null").cache()
final_site = final_site.filter("(`article.published_time` is not null) or (`og.published_time` is not null) or \
                        (`og.modified_time` is not null) or (`article.modified_time` is not null)")

final_site = final_site.withColumn("published_time_tz", to_timestamp(coalesce("`article.published_time`", "`og.published_time`")))
final_site = final_site.withColumn("modified_time_tz", to_timestamp(coalesce("`article.modified_time`", "`og.modified_time`")))
final_site = final_site.drop(col("`article.modified_time`")).drop(col("`article.published_time`")).drop(col("`og.published_time`")).drop(col("`og.modified_time`"))

final_site = final_site.withColumn("category", get_category_udf(struct(final_site['`og.url`'])))

final_site = final_site.withColumn("published_time_tz_rome_year", date_format(col("published_time_tz"), "yyyy")) \
    .withColumn("published_time_tz_rome_month", date_format(col("published_time_tz"), "MM")) \
    .withColumn("published_time_tz_rome_day", date_format(col("published_time_tz"), "dd")) \
    .withColumn("published_time_tz_rome_hour", date_format(col("published_time_tz"), "HH")) \
    .withColumn("published_time_tz_rome_YM", date_format(col("published_time_tz"), "YMM"))

final_site = final_site.withColumn("modified_time_tz_rome_year", date_format(col("modified_time_tz"), "yyyy")) \
    .withColumn("modified_time_tz_rome_month", date_format(col("modified_time_tz"), "MM")) \
    .withColumn("modified_time_tz_rome_day", date_format(col("modified_time_tz"), "dd")) \
    .withColumn("modified_time_tz_rome_hour", date_format(col("modified_time_tz"), "HH")) \
    .withColumn("modified_time_tz_rome_YM", date_format(col("modified_time_tz"), "YMM"))

final_site = final_site.withColumn("year", coalesce(col("modified_time_tz_rome_year"), col("published_time_tz_rome_year"))). \
    withColumn("month", coalesce(col("modified_time_tz_rome_month"), col("published_time_tz_rome_month"))). \
    withColumn("day", coalesce(col("modified_time_tz_rome_day"), col("published_time_tz_rome_day"))). \
    withColumn("hour", coalesce(col("modified_time_tz_rome_hour"), col("published_time_tz_rome_hour")))

final_site = final_site.filter("int(concat(year,month,day,hour)) >= %d%02d%02d%02d" % (date_start.year,date_start.month,date_start.day, date_start.hour)). \
    filter("int(concat(year,month,day,hour)) <= %d%02d%02d%02d" % (date.year,date.month,date.day, date.hour))

final_site = final_site.withColumn("day_of_week", date_format(coalesce(col("published_time_tz"), col("modified_time_tz")), "EEEE"))
final_site = final_site.withColumn("is_weekend", when((col("day_of_week") == "Saturday") | (col("day_of_week") == "Sunday"), True).otherwise(False))
#final_site = final_site.withColumn("day_of_week", get_day_in_italian_udf(struct(final_site['day_of_week'])))
final_site = final_site.withColumn("edition", get_edition_udf(struct(final_site['`og.url`'])))

columns_to_rename = [ i for i in columns if '.' in i]

for column in columns:
    final_site = final_site.withColumnRenamed(column, column.replace('.', '_'))

w = Window.partitionBy("og_url").orderBy(coalesce(col("modified_time_tz"), col("published_time_tz")).desc())
final_site.select("year", "month", "day", "hour", "og_url","html","published_time_tz", "modified_time_tz"). \
    withColumn("rn", row_number().over(w)).filter("rn = 1").drop("rn").drop("published_time_tz", "modified_time_tz"). \
    write.partitionBy("year", "month", "day", "hour").mode("overwrite").parquet(f"gs://{bucket_published}/{site}_html")

final_site = final_site.withColumn("isAccessibleForFree", when(final_site.html.contains('isAccessibleForFree": false'), "LOCKED").otherwise("FREE"))
datetime_now = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")
final_site = final_site.withColumn("audit_time", lit(datetime_now))
final_site = final_site.drop("html").drop_duplicates().cache()
final_site.show(1,False)
try:
    site_old = spark.read.schema(final_site.schema).parquet(f"gs://{bucket_published}/{site}_V2/").filter("int(concat(year,month,day,hour)) >= %d%02d%02d%02d" % (date_start.year,date_start.month,date_start.day, date_start.hour)). \
        filter("int(concat(year,month,day,hour)) <= %d%02d%02d%02d" % (date.year,date.month,date.day, date.hour)).select([c for c in final_site.columns]).cache()
    site_old.createTempView('_old_hour')
    final_site.createTempView('_now')
    final_site = spark.sql("select * from _old_hour union all select * from _now")
except Exception as e:
    print(e)
finally:
    win_mapping_url = Window.partitionBy(['modified_time_tz', 'og_url']).orderBy(col('audit_time').desc())
    final_site = final_site.withColumn('most_recent', row_number().over(win_mapping_url))
    final_site = final_site.filter(col('most_recent') == 1).drop('most_recent')
    final_site.write.partitionBy('year', 'month', 'day', 'hour').parquet(f"gs://{bucket_published}/{site}_V2/", mode="overwrite")
    spark.catalog.clearCache()
    spark.stop()

# -------------------------------- PHASE PUBLISHED END
