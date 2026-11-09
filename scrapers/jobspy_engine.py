import logging
from .base_scraper import BaseScraper, JobResult

import asyncio

logger = logging.getLogger(__name__)

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    logger.warning("jobspy is not installed. JobSpyScraper will not function properly.")

class JobSpyScraper(BaseScraper):
    @property
    def name(self) -> str:
        return 'jobspy'
        
    def __init__(self, proxy_list: list[str] | None = None):
        self.proxy_list = proxy_list
        
    async def scrape(self, query: str, location: str = 'India', sites: list[str] = None, max_results: int = 50, hours_old: int = 72, **kwargs) -> list[JobResult]:
        if not JOBSPY_AVAILABLE:
            logger.error("Cannot scrape, jobspy is not installed")
            return []
            
        if sites is None:
            sites = ['linkedin', 'indeed', 'glassdoor', 'naukri', 'google']
            
        try:
            country_indeed = "india" if "india" in location.lower() else "usa"
            jobs_df = await asyncio.to_thread(
                scrape_jobs,
                site_name=sites,
                search_term=query,
                location=location,
                results_wanted=max_results,
                hours_old=hours_old,
                country_indeed=country_indeed,
                proxies=self.proxy_list
            )
            
            results = []
            if jobs_df is not None and not jobs_df.empty:
                for _, row in jobs_df.iterrows():
                    desc = str(row.get('description', '') or '')
                    tech = self._extract_tech_stack(desc)
                    
                    min_sal, max_sal = None, None
                    try:
                        raw_min = row.get('min_amount')
                        if raw_min and str(raw_min).lower() != 'nan':
                            min_sal = float(raw_min)
                        raw_max = row.get('max_amount')
                        if raw_max and str(raw_max).lower() != 'nan':
                            max_sal = float(raw_max)
                    except (ValueError, TypeError):
                        pass

                    job_url_val = row.get('job_url')
                    if not job_url_val or str(job_url_val).lower() == 'nan':
                        continue

                    title_val = str(row.get('title') or 'Unknown')
                    comp_val = str(row.get('company') or 'Unknown')
                    loc_val = str(row.get('location') or location)
                    is_remote_val = bool(row.get('is_remote', False)) if str(row.get('is_remote', '')).lower() != 'nan' else False
                    
                    res = JobResult(
                        title=title_val if title_val != 'nan' else 'Unknown Role',
                        company=comp_val if comp_val != 'nan' else 'Unknown Company',
                        location=loc_val if loc_val != 'nan' else location,
                        job_url=str(job_url_val),
                        source=str(row.get('site', self.name)),
                        description=desc if desc != 'nan' else '',
                        is_remote=is_remote_val,
                        salary_min=min_sal,
                        salary_max=max_sal,
                        tech_stack=tech
                    )
                    results.append(res)
            return results
        except Exception as e:
            logger.exception(f"Error in JobSpyScraper: {e}")
            return []
            
    async def scrape_for_profile(self, profile: dict) -> list[JobResult]:
        roles = profile.get('target_roles', [])
        all_results = []
        seen_urls = set()
        
        for role in roles:
            jobs = await self.scrape(query=role, location=profile.get('location', 'India'))
            for j in jobs:
                if j.job_url not in seen_urls:
                    seen_urls.add(j.job_url)
                    all_results.append(j)
                    
        return all_results
