BOT_NAME = "allecijfers"

SPIDER_MODULES = ["allecijfers.spiders"]
NEWSPIDER_MODULE = "allecijfers.spiders"

ADDONS = {}

USER_AGENT = "Mozilla/5.0 (compatible; allecijfers-scraper/1.0)"

ROBOTSTXT_OBEY = True

CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 0

RETRY_TIMES = 3

ITEM_PIPELINES = {
    "allecijfers.pipelines.SQLitePipeline": 300,
}

SQLITE_DATABASE = "data/allecijfers.db"

FEED_EXPORT_ENCODING = "utf-8"

TELNETCONSOLE_ENABLED = False

LOG_LEVEL = "INFO"
