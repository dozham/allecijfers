import scrapy


class StatsItem(scrapy.Item):
    municipality = scrapy.Field()
    area_type    = scrapy.Field()  # "wijk" | "buurt"
    area_slug    = scrapy.Field()  # from URL path segment
    area_name    = scrapy.Field()  # from <span itemprop='name'>
    url          = scrapy.Field()
    category     = scrapy.Field()  # first <th> of each stats table
    topic        = scrapy.Field()  # first <td> of each data row
    value        = scrapy.Field()  # second <td> (raw string)
    unit         = scrapy.Field()  # third <td>
    year         = scrapy.Field()  # fourth <td>
    scraped_at   = scrapy.Field()  # ISO-8601 UTC timestamp
