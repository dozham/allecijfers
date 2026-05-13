import sqlite3
import os
from itemadapter import ItemAdapter


class SQLitePipeline:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.buffer = []
        self.BATCH_SIZE = 500

    @classmethod
    def from_crawler(cls, crawler):
        return cls(db_path=crawler.settings.get("SQLITE_DATABASE", "data/allecijfers.db"))

    def open_spider(self, spider=None):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id           INTEGER PRIMARY KEY,
                municipality TEXT    NOT NULL,
                area_type    TEXT    NOT NULL,
                area_slug    TEXT    NOT NULL,
                area_name    TEXT,
                url          TEXT    NOT NULL,
                category     TEXT,
                topic        TEXT    NOT NULL,
                value        TEXT,
                unit         TEXT,
                year         TEXT,
                scraped_at   TEXT    NOT NULL,
                UNIQUE (area_slug, area_type, topic)
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON stats(topic)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_slug  ON stats(area_slug)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_type  ON stats(area_type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_slug_type ON stats(area_slug, area_type);")
        self.conn.commit()

    def process_item(self, item, spider=None):
        a = ItemAdapter(item)
        self.buffer.append((
            a.get("municipality"),
            a.get("area_type"),
            a.get("area_slug"),
            a.get("area_name"),
            a.get("url"),
            a.get("category"),
            a.get("topic"),
            a.get("value"),
            a.get("unit"),
            a.get("year"),
            a.get("scraped_at"),
        ))
        if len(self.buffer) >= self.BATCH_SIZE:
            self._flush()
        return item

    def close_spider(self, spider=None):
        self._flush()
        self.conn.close()

    def _flush(self):
        if not self.buffer:
            return
        self.conn.executemany(
            "INSERT OR REPLACE INTO stats VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?)",
            self.buffer,
        )
        self.conn.commit()
        self.buffer.clear()
