import asyncio
import logging
from pathlib import Path
import httpx
import yaml
from .base_scraper import BaseScraper, JobResult

logger = logging.getLogger(__name__)

class ATSScraper(BaseScraper):
    @property
    def name(self) -> str:
        return 'ats_direct'
        
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15, headers={'User-Agent': 'career-ops-india/2.0'})
        
    async def scrape_greenhouse(self, slug: str, company_name: str) -> list[JobResult]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        results = []
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            for job in data.get('jobs', []):
                title = job.get('title', '')
                loc = job.get('location', {}).get('name', '')
                job_url = job.get('absolute_url', '')
                desc = job.get('content', '')
                tech = self._extract_tech_stack(desc)
                results.append(JobResult(
                    title=title,
                    company=company_name,
                    location=loc,
                    job_url=job_url,
                    source=self.name,
                    ats_platform='greenhouse',
                    description=desc,
                    tech_stack=tech
                ))
        except Exception as e:
            logger.error(f"Error scraping greenhouse for {slug}: {e}")
        return results

    async def scrape_lever(self, slug: str, company_name: str) -> list[JobResult]:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        results = []
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            for job in data:
                title = job.get('text', '')
                loc = job.get('categories', {}).get('location', '')
                job_url = job.get('hostedUrl', '')
                desc = job.get('descriptionPlain', '')
                tech = self._extract_tech_stack(desc)
                results.append(JobResult(
                    title=title,
                    company=company_name,
                    location=loc,
                    job_url=job_url,
                    source=self.name,
                    ats_platform='lever',
                    description=desc,
                    tech_stack=tech
                ))
        except Exception as e:
            logger.error(f"Error scraping lever for {slug}: {e}")
        return results

    async def scrape_ashby(self, slug: str, company_name: str) -> list[JobResult]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        results = []
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            for job in data.get('jobs', []):
                title = job.get('title', '')
                loc = job.get('location', '')
                job_url = job.get('jobUrl', '')
                results.append(JobResult(
                    title=title,
                    company=company_name,
                    location=loc,
                    job_url=job_url,
                    source=self.name,
                    ats_platform='ashby'
                ))
        except Exception as e:
            logger.error(f"Error scraping ashby for {slug}: {e}")
        return results

    async def scrape_workday(self, company: str, board: str, company_name: str) -> list[JobResult]:
        url = f"https://{company}.wd1.myworkdayjobs.com/wday/cxs/{company}/{board}/jobs"
        results = []
        try:
            payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            for job in data.get('jobPostings', []):
                title = job.get('title', '')
                loc = job.get('locationsText', '')
                url_path = job.get('externalPath', '')
                job_url = f"https://{company}.wd1.myworkdayjobs.com/en-US/{company}/{board}{url_path}"
                results.append(JobResult(
                    title=title,
                    company=company_name,
                    location=loc,
                    job_url=job_url,
                    source=self.name,
                    ats_platform='workday'
                ))
        except Exception as e:
            logger.error(f"Error scraping workday for {company}: {e}")
        return results

    async def scrape_smartrecruiters(self, slug: str, company_name: str) -> list[JobResult]:
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        results = []
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            for job in data.get('content', []):
                title = job.get('name', '')
                loc = job.get('location', {}).get('city', '')
                job_url = f"https://jobs.smartrecruiters.com/{slug}/{job.get('id')}"
                results.append(JobResult(
                    title=title,
                    company=company_name,
                    location=loc,
                    job_url=job_url,
                    source=self.name,
                    ats_platform='smartrecruiters'
                ))
        except Exception as e:
            logger.error(f"Error scraping smartrecruiters for {slug}: {e}")
        return results

    async def scrape_bamboohr(self, slug: str, company_name: str) -> list[JobResult]:
        url = f"https://{slug}.bamboohr.com/careers/list"
        results = []
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            for job in data.get('result', []):
                title = job.get('jobOpeningName', '')
                loc = job.get('location', {}).get('city', '')
                job_id = job.get('id')
                job_url = f"https://{slug}.bamboohr.com/careers/{job_id}"
                results.append(JobResult(
                    title=title,
                    company=company_name,
                    location=loc,
                    job_url=job_url,
                    source=self.name,
                    ats_platform='bamboohr'
                ))
        except Exception as e:
            logger.error(f"Error scraping bamboohr for {slug}: {e}")
        return results

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def scrape_all_from_portals(self, portals_path='portals/india.yml') -> list[JobResult]:
        path = Path(portals_path)
        if not path.exists():
            repo_root = Path(__file__).resolve().parent.parent
            path = repo_root / portals_path
            if not path.exists():
                logger.error(f"portals file not found at: {portals_path}")
                return []
                
        try:
            with open(path, 'r', encoding='utf-8') as f:
                portals = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")
            return []

        if not portals or not isinstance(portals, dict):
            return []
            
        all_results = []
        semaphore = asyncio.Semaphore(10)
        
        async def fetch(ats_type: str, entry: dict):
            if not isinstance(entry, dict) or not entry.get('name'):
                return []
            slug = entry.get('slug', '')
            name = entry.get('name', '')
            ats_lower = ats_type.lower()
            
            async with semaphore:
                try:
                    if ats_lower == 'greenhouse' and slug:
                        return await self.scrape_greenhouse(slug, name)
                    elif ats_lower == 'lever' and slug:
                        return await self.scrape_lever(slug, name)
                    elif ats_lower == 'ashby' and slug:
                        return await self.scrape_ashby(slug, name)
                    elif ats_lower == 'workday':
                        comp = entry.get('company', slug)
                        board = entry.get('board', 'external')
                        return await self.scrape_workday(comp, board, name)
                    elif ats_lower == 'smartrecruiters' and slug:
                        return await self.scrape_smartrecruiters(slug, name)
                    elif ats_lower == 'bamboohr' and slug:
                        return await self.scrape_bamboohr(slug, name)
                except Exception as e:
                    logger.debug(f"Fetch failed for {name} ({ats_type}): {e}")
                return []
                
        tasks = []
        for ats_type, entries in portals.items():
            if isinstance(entries, list):
                for entry in entries:
                    tasks.append(fetch(ats_type, entry))
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                all_results.extend(res)
                
        return all_results
        
    async def scrape(self, query: str = None, location: str = None, **kwargs) -> list[JobResult]:
        jobs = await self.scrape_all_from_portals()
        if query:
            q = query.lower()
            jobs = [j for j in jobs if q in j.title.lower() or (j.description and q in j.description.lower())]
        if location:
            loc_q = location.lower()
            jobs = [j for j in jobs if not j.location or loc_q in j.location.lower() or j.is_remote]
        return jobs
        
    async def close(self):
        if not self.client.is_closed:
            await self.client.aclose()
