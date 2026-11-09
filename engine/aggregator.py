"""
Job Aggregator — Orchestrates all 5 tiers of job scraping.

Tier 1: Direct ATS APIs (Greenhouse, Lever, Ashby, Workday, SmartRecruiters) — ZERO ban risk
Tier 2: Free Job Aggregator APIs (Remotive, Arbeitnow, Adzuna, The Muse) — ZERO ban risk
Tier 3: RSS Feeds (WeWorkRemotely, RemoteOK, Himalayas, Remotive) — ZERO ban risk
Tier 4: JobSpy multi-board (LinkedIn, Indeed, Glassdoor, Naukri, Google) — LOW-MODERATE risk
Tier 5: Stealth scrapers (Naukri Camoufox, CutShort, Instahyre, Wellfound) — existing scripts
"""

import asyncio
import logging
import datetime
from pathlib import Path
from typing import Optional

from engine.deduplicator import JobDeduplicator
from engine.job_matcher import JobMatcher
from db.job_store import JobStore

logger = logging.getLogger(__name__)


class JobAggregator:
    """Orchestrates all 5 tiers of job scraping, deduplication, scoring, and storage."""

    def __init__(
        self,
        db_path: str = "data/career_ops.db",
        profile_path: str = "config/profile.yml",
    ):
        self.db_path = db_path
        self.profile_path = profile_path

        self.store = JobStore(db_path=db_path)
        self.deduplicator = JobDeduplicator()
        self.matcher = JobMatcher(profile_path=profile_path)

        # Load profile for query generation
        self._profile = self.matcher.profile
        self._target_roles = (
            self._profile.get("candidate", {}).get("target_roles", [])
        )

    def _job_results_to_dicts(self, job_results: list) -> list[dict]:
        """Convert list of JobResult pydantic models to dicts for dedup/scoring."""
        dicts = []
        for jr in job_results:
            d = jr.model_dump() if hasattr(jr, "model_dump") else vars(jr)
            d["id"] = jr.generate_id() if hasattr(jr, "generate_id") else None
            # Map salary_min/salary_max for the matcher
            if d.get("salary_min") or d.get("salary_max"):
                parts = []
                if d.get("salary_min"):
                    parts.append(str(d["salary_min"]))
                if d.get("salary_max"):
                    parts.append(str(d["salary_max"]))
                d["salary_listed"] = "-".join(parts) + " LPA"
            dicts.append(d)
        return dicts

    def _process_results(self, raw_jobs: list, source_label: str) -> dict:
        """Deduplicate, score, store, and return stats."""
        if not raw_jobs:
            return {
                "source": source_label,
                "jobs_found": 0,
                "jobs_new": 0,
                "jobs_updated": 0,
            }

        # Deduplicate
        deduped = self.deduplicator.deduplicate(raw_jobs)

        # Score
        scored = self.matcher.score_jobs(deduped)

        # Store in DB
        db_ready = []
        for job in scored:
            entry = {k: v for k, v in job.items() if k != "dimension_scores"}
            entry["fit_score"] = job.get("score")
            entry["grade"] = job.get("grade")
            entry["scoring_details"] = job.get("dimension_scores")
            # Generate description snippet
            desc = job.get("description", "") or ""
            entry["description_snippet"] = desc[:500] if desc else None
            db_ready.append(entry)

        new_count, updated_count = self.store.upsert_jobs(db_ready)

        # Log scrape run
        self.store.log_scrape_run(
            source=source_label,
            jobs_found=len(raw_jobs),
            jobs_new=new_count,
            jobs_updated=updated_count,
            status="completed",
        )

        logger.info(
            f"[{source_label}] Found {len(raw_jobs)} → Deduped {len(deduped)} → "
            f"New {new_count}, Updated {updated_count}"
        )

        return {
            "source": source_label,
            "jobs_found": len(raw_jobs),
            "jobs_deduped": len(deduped),
            "jobs_new": new_count,
            "jobs_updated": updated_count,
        }

    # ─── Tier 1: Direct ATS APIs ─────────────────────────────────────────

    async def run_tier1_ats(self) -> dict:
        """Tier 1: Direct ATS APIs (zero ban risk).
        Scrapes Greenhouse, Lever, Ashby, Workday, SmartRecruiters, BambooHR
        for all companies in portals/india.yml."""
        logger.info("🟢 Tier 1: Scanning ATS APIs...")
        try:
            from scrapers.ats_engine import ATSScraper

            scraper = ATSScraper()
            try:
                jobs = await scraper.scrape_all_from_portals()
                dicts = self._job_results_to_dicts(jobs)
                return self._process_results(dicts, "tier1_ats")
            finally:
                await scraper.close()
        except ImportError as e:
            logger.error(f"ATS scraper import error: {e}")
            return {"source": "tier1_ats", "error": str(e), "jobs_found": 0}
        except Exception as e:
            logger.exception(f"Tier 1 error: {e}")
            return {"source": "tier1_ats", "error": str(e), "jobs_found": 0}

    # ─── Tier 2: Job Aggregator APIs ─────────────────────────────────────

    async def run_tier2_apis(self, query: Optional[str] = None) -> dict:
        """Tier 2: Job aggregator APIs (zero ban risk).
        Queries Remotive, Arbeitnow, Adzuna, The Muse."""
        logger.info("🟢 Tier 2: Querying job aggregator APIs...")
        search_query = query or (self._target_roles[0] if self._target_roles else "software engineer")
        try:
            from scrapers.api_aggregator import APIAggregator

            scraper = APIAggregator()
            jobs = await scraper.scrape_all(query=search_query, location="India")
            dicts = self._job_results_to_dicts(jobs)
            return self._process_results(dicts, "tier2_apis")
        except ImportError as e:
            logger.error(f"API aggregator import error: {e}")
            return {"source": "tier2_apis", "error": str(e), "jobs_found": 0}
        except Exception as e:
            logger.exception(f"Tier 2 error: {e}")
            return {"source": "tier2_apis", "error": str(e), "jobs_found": 0}

    # ─── Tier 3: RSS Feeds ───────────────────────────────────────────────

    async def run_tier3_rss(self) -> dict:
        """Tier 3: RSS feeds (zero ban risk).
        Reads WeWorkRemotely, RemoteOK, Himalayas, Remotive feeds."""
        logger.info("🟢 Tier 3: Reading RSS feeds...")
        try:
            from scrapers.rss_reader import RSSJobReader

            reader = RSSJobReader()
            jobs = await reader.scrape_all_feeds()
            dicts = self._job_results_to_dicts(jobs)
            return self._process_results(dicts, "tier3_rss")
        except ImportError as e:
            logger.error(f"RSS reader import error: {e}")
            return {"source": "tier3_rss", "error": str(e), "jobs_found": 0}
        except Exception as e:
            logger.exception(f"Tier 3 error: {e}")
            return {"source": "tier3_rss", "error": str(e), "jobs_found": 0}

    # ─── Tier 4: JobSpy Multi-Board ──────────────────────────────────────

    async def run_tier4_jobspy(self, queries: Optional[list[str]] = None) -> dict:
        """Tier 4: JobSpy multi-board scraping (LinkedIn, Indeed, Glassdoor, Naukri, Google).
        Uses curl_cffi for TLS fingerprint impersonation."""
        logger.info("🟡 Tier 4: Running JobSpy multi-board scraper...")
        search_queries = queries or self._target_roles or ["software engineer"]
        try:
            from scrapers.jobspy_engine import JobSpyScraper

            scraper = JobSpyScraper()
            all_jobs = []
            seen_urls = set()

            for q in search_queries:
                logger.info(f"  JobSpy searching: '{q}'")
                jobs = await scraper.scrape(query=q, location="India", max_results=50)
                for j in jobs:
                    if j.job_url not in seen_urls:
                        seen_urls.add(j.job_url)
                        all_jobs.append(j)

            dicts = self._job_results_to_dicts(all_jobs)
            return self._process_results(dicts, "tier4_jobspy")
        except ImportError as e:
            logger.error(f"JobSpy import error: {e}")
            return {"source": "tier4_jobspy", "error": str(e), "jobs_found": 0}
        except Exception as e:
            logger.exception(f"Tier 4 error: {e}")
            return {"source": "tier4_jobspy", "error": str(e), "jobs_found": 0}

    # ─── Orchestration ───────────────────────────────────────────────────

    async def run_all(self, queries: Optional[list[str]] = None) -> dict:
        """Run all tiers sequentially, deduplicate, score, and store.
        Returns combined summary stats."""
        logger.info("🚀 Running ALL scraping tiers...")
        results = []

        # Run tiers sequentially (Tier 1-3 are safe, Tier 4 needs rate limiting)
        results.append(await self.run_tier1_ats())
        results.append(await self.run_tier2_apis(queries[0] if queries else None))
        results.append(await self.run_tier3_rss())
        results.append(await self.run_tier4_jobspy(queries))

        total_found = sum(r.get("jobs_found", 0) for r in results)
        total_new = sum(r.get("jobs_new", 0) for r in results)
        total_updated = sum(r.get("jobs_updated", 0) for r in results)

        summary = {
            "total_jobs_found": total_found,
            "total_new": total_new,
            "total_updated": total_updated,
            "tier_results": results,
            "db_stats": self.store.get_stats(),
        }

        logger.info(
            f"✅ Scan complete: {total_found} found, {total_new} new, {total_updated} updated"
        )
        return summary

    async def run_safe(self, queries: Optional[list[str]] = None) -> dict:
        """Run only Tier 1-3 (zero ban risk tiers)."""
        logger.info("🛡️ Running SAFE tiers only (1-3)...")
        results = []

        results.append(await self.run_tier1_ats())
        results.append(await self.run_tier2_apis(queries[0] if queries else None))
        results.append(await self.run_tier3_rss())

        total_found = sum(r.get("jobs_found", 0) for r in results)
        total_new = sum(r.get("jobs_new", 0) for r in results)

        return {
            "total_jobs_found": total_found,
            "total_new": total_new,
            "tier_results": results,
            "db_stats": self.store.get_stats(),
        }

    # ─── Query Methods ───────────────────────────────────────────────────

    def get_top_matches(
        self, min_grade: str = "C", limit: int = 50
    ) -> list[dict]:
        """Get top job matches from database, filtered by minimum grade."""
        grade_order = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
        min_val = grade_order.get(min_grade.upper(), 3)

        jobs = self.store.get_active_jobs()
        results = []
        for job in jobs:
            job_grade_val = grade_order.get(job.grade, 0) if job.grade else 0
            if job_grade_val >= min_val:
                results.append(
                    {
                        "id": job.id,
                        "title": job.title,
                        "company": job.company,
                        "location": job.location,
                        "salary_min": job.salary_min,
                        "salary_max": job.salary_max,
                        "source": job.source,
                        "job_url": job.job_url,
                        "score": job.fit_score,
                        "grade": job.grade,
                        "date_posted": str(job.date_posted) if job.date_posted else None,
                        "is_remote": job.is_remote,
                    }
                )

        results.sort(key=lambda x: x.get("score") or 0, reverse=True)
        return results[:limit]

    def get_summary(self) -> dict:
        """Get overall pipeline summary from database."""
        db_stats = self.store.get_stats()
        pipeline_stats = self.store.get_pipeline_stats()
        return {
            "job_stats": db_stats,
            "pipeline_stats": pipeline_stats,
        }
