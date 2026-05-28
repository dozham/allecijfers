import scrapy
from datetime import datetime, timezone
from allecijfers.items import HierarchyItem, StatsItem


class NeighborhoodSpider(scrapy.Spider):
    """Scrape all wijk/buurt stats for a given municipality.

    Usage:
        scrapy crawl neighborhood -a municipality=amsterdam
        scrapy crawl neighborhood -a municipality=utrecht
        scrapy crawl neighborhood -a municipality=haarlem
    """

    name = "neighborhood"
    municipality = "amsterdam"  # default; override with -a municipality=<name>

    async def start(self):
        url = f"https://allecijfers.nl/gemeente-overzicht/{self.municipality}/"
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        scraped_at = datetime.now(timezone.utc).isoformat()
        seen = set()
        for href in response.css("a[href]::attr(href)").getall():
            if "/wijk/" not in href and "/buurt/" not in href:
                continue
            url = response.urljoin(href).split("#")[0].rstrip("/") + "/"
            if url in seen:
                continue
            seen.add(url)
            yield scrapy.Request(
                url,
                callback=self.parse_neighborhood,
                cb_kwargs={"scraped_at": scraped_at},
            )

    def parse_neighborhood(self, response, scraped_at):
        path = response.url.rstrip("/").rsplit("/", 1)[-1]
        area_type = "wijk" if "/wijk/" in response.url else "buurt"

        raw_name = response.css("span[itemprop='name']::text").get("")
        area_name = raw_name.strip()
        for prefix in ("wijk ", "buurt "):
            if area_name.lower().startswith(prefix):
                area_name = area_name[len(prefix):]
                break

        found_any = False
        for table in response.css("table"):
            headers = table.css("thead th::text").getall()
            if len(headers) != 4 or headers[1] != "Waarde" or headers[2] != "Eenheid" or headers[3] != "Jaar":
                continue
            category = headers[0]
            found_any = True
            for row in table.css("tbody tr"):
                cells = row.css("td::text").getall()
                if len(cells) != 4:
                    continue
                yield StatsItem(
                    municipality=self.municipality,
                    area_type=area_type,
                    area_slug=path,
                    area_name=area_name,
                    url=response.url,
                    category=category,
                    topic=cells[0].strip(),
                    value=cells[1].strip(),
                    unit=cells[2].strip(),
                    year=cells[3].strip(),
                    scraped_at=scraped_at,
                )

        if not found_any:
            self.logger.warning("No stats tables found at %s", response.url)

        if area_type == "wijk":
            for href in response.css("a[href]::attr(href)").getall():
                if "/buurt/" not in href:
                    continue
                buurt_slug = href.rstrip("/").rsplit("/", 1)[-1]
                buurt_name = response.css(
                    f"a[href*='/{buurt_slug}/']::text"
                ).get("").strip()
                if buurt_slug and buurt_name:
                    yield HierarchyItem(
                        municipality=self.municipality,
                        wijk_slug=path,
                        wijk_name=area_name,
                        buurt_slug=buurt_slug,
                        buurt_name=buurt_name,
                    )
