import asyncio
import logging
import os
import httpx
from .base_scraper import BaseScraper, JobResult

logger = logging.getLogger(__name__)

class APIAggregator(BaseScraper):
    @property
    def name(self) -> str:
        return 'api_aggregator'
        
    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 career-ops/2.0'},
            timeout=15,
            follow_redirects=True
        )

    async def scrape_remotive(self, query: str = None) -> list[JobResult]:
        url = "https://remotive.com/api/remote-jobs"
        params = {}
        if query:
            params['search'] = query
        results = []
        try:
            async with self._get_client() as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                for job in data.get('jobs', []):
                    desc = job.get('description', '') or ''
                    results.append(JobResult(
                        title=job.get('title', ''),
                        company=job.get('company_name', ''),
                        location=job.get('candidate_required_location', 'Remote'),
                        is_remote=True,
                        job_url=job.get('url', ''),
                        source="remotive",
                        description=desc,
                        tech_stack=self._extract_tech_stack(desc)
                    ))
        except Exception as e:
            logger.error(f"Error scraping remotive: {e}")
        return results
        
    async def scrape_arbeitnow(self, query: str = None) -> list[JobResult]:
        url = "https://www.arbeitnow.com/api/job-board-api"
        results = []
        try:
            async with self._get_client() as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                for job in data.get('data', []):
                    title = job.get('title', '')
                    if query and query.lower() not in title.lower():
                        continue
                    desc = job.get('description', '') or ''
                    results.append(JobResult(
                        title=title,
                        company=job.get('company_name', ''),
                        location=job.get('location', ''),
                        is_remote=job.get('remote', False),
                        job_url=job.get('url', ''),
                        source="arbeitnow",
                        description=desc,
                        tech_stack=self._extract_tech_stack(desc)
                    ))
        except Exception as e:
            logger.error(f"Error scraping arbeitnow: {e}")
        return results

    async def scrape_adzuna(self, query: str = None, location: str = 'in', api_id: str = None, api_key: str = None) -> list[JobResult]:
        api_id = api_id or os.getenv('ADZUNA_APP_ID')
        api_key = api_key or os.getenv('ADZUNA_APP_KEY')
        if not api_id or not api_key:
            return []
            
        loc_code = 'in' if 'ind' in (location or '').lower() else (location or 'in')
        url = f"https://api.adzuna.com/v1/api/jobs/{loc_code}/search/1"
        params = {
            'app_id': api_id,
            'app_key': api_key,
        }
        if query:
            params['what'] = query
            
        results = []
        try:
            async with self._get_client() as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                for job in data.get('results', []):
                    desc = job.get('description', '') or ''
                    sal_min = job.get('salary_min')
                    sal_max = job.get('salary_max')
                    # Adzuna INR salaries are per-annum
                    if sal_min and sal_min > 10000:
                        sal_min = round(sal_min / 100000, 2)
                    if sal_max and sal_max > 10000:
                        sal_max = round(sal_max / 100000, 2)

                    results.append(JobResult(
                        title=job.get('title', ''),
                        company=job.get('company', {}).get('display_name', ''),
                        location=job.get('location', {}).get('display_name', ''),
                        salary_min=sal_min,
                        salary_max=sal_max,
                        job_url=job.get('redirect_url', ''),
                        source="adzuna",
                        description=desc,
                        tech_stack=self._extract_tech_stack(desc)
                    ))
        except Exception as e:
            logger.error(f"Error scraping adzuna: {e}")
        return results

    async def scrape_the_muse(self, query: str = None, location: str = None) -> list[JobResult]:
        url = "https://www.themuse.com/api/public/jobs?page=1&descending=true"
        results = []
        try:
            async with self._get_client() as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                for job in data.get('results', []):
                    title = job.get('name', '')
                    if query and query.lower() not in title.lower():
                        continue
                    locs = job.get('locations', [])
                    loc_name = locs[0].get('name') if locs else ''
                    desc = job.get('contents', '') or ''
                    results.append(JobResult(
                        title=title,
                        company=job.get('company', {}).get('name', ''),
                        location=loc_name,
                        job_url=job.get('refs', {}).get('landing_page', ''),
                        source="themuse",
                        description=desc,
                        tech_stack=self._extract_tech_stack(desc)
                    ))
        except Exception as e:
            logger.error(f"Error scraping the muse: {e}")
        return results

    async def scrape_all(self, query: str = None, location: str = 'India') -> list[JobResult]:
        tasks = [
            self.scrape_remotive(query),
            self.scrape_arbeitnow(query),
            self.scrape_adzuna(query, location),
            self.scrape_the_muse(query)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_results = []
        for res in results:
            if isinstance(res, list):
                all_results.extend(res)
        return all_results
        
    async def scrape(self, query: str = None, location: str = 'in', **kwargs) -> list[JobResult]:
        return await self.scrape_all(query, location)
