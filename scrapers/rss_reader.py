import asyncio
import logging
import httpx
from .base_scraper import BaseScraper, JobResult

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

logger = logging.getLogger(__name__)

class RSSJobReader(BaseScraper):
    FEEDS = {
        'weworkremotely': 'https://weworkremotely.com/remote-jobs.rss',
        'remoteok': 'https://remoteok.com/remote-jobs.rss',
        'himalayas': 'https://himalayas.app/jobs/rss',
        'remotive': 'https://remotive.com/feed',
    }

    @property
    def name(self) -> str:
        return 'rss_feeds'
        
    async def scrape_feed(self, feed_name: str, feed_url: str) -> list[JobResult]:
        if not FEEDPARSER_AVAILABLE:
            logger.error("feedparser not available")
            return []
            
        results = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 career-ops/2.0'
        }
        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
                resp = await client.get(feed_url, timeout=15)
                resp.raise_for_status()
                feed = feedparser.parse(resp.text)
                
                for entry in feed.entries:
                    raw_title = entry.get('title', '').strip()
                    author = entry.get('author', '').strip()
                    company = author or 'Unknown'
                    title = raw_title
                    
                    # Many RSS feeds format as "Company: Job Title" or "Job Title at Company"
                    if company == 'Unknown' and ':' in raw_title:
                        parts = raw_title.split(':', 1)
                        company = parts[0].strip()
                        title = parts[1].strip()
                    elif company == 'Unknown' and ' at ' in raw_title:
                        parts = raw_title.split(' at ', 1)
                        title = parts[0].strip()
                        company = parts[1].strip()

                    desc = entry.get('description', '') or ''
                    results.append(JobResult(
                        title=title or raw_title,
                        company=company,
                        job_url=entry.get('link', ''),
                        source=f"rss_{feed_name}",
                        description=desc,
                        is_remote=True,
                        tech_stack=self._extract_tech_stack(desc)
                    ))
        except Exception as e:
            logger.error(f"Error parsing feed {feed_name}: {e}")
        return results
        
    async def scrape_all_feeds(self) -> list[JobResult]:
        tasks = []
        for name, url in self.FEEDS.items():
            tasks.append(self.scrape_feed(name, url))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_results = []
        for res in results:
            if isinstance(res, list):
                all_results.extend(res)
        return all_results
        
    async def scrape(self, query: str = None, location: str = None, **kwargs) -> list[JobResult]:
        jobs = await self.scrape_all_feeds()
        if query:
            q = query.lower()
            jobs = [j for j in jobs if q in j.title.lower() or (j.description and q in j.description.lower())]
        return jobs
