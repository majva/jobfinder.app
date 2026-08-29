from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from src.infrastructure.di.inject import inject
from src.infrastructure.utils.config_reader import ConfigReader

_JOB_ID_RE = re.compile(r"(?:jobPosting:|/jobs/view/|currentJobId=)(\d{8,})")
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.linkedin.com/jobs/search",
}


class LinkedInUnavailableError(RuntimeError):
    pass


@dataclass
class LinkedInListing:
    linkedin_job_id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    url: str = ""
    posted_at: Optional[str] = None
    salary_hint: Optional[str] = None
    workplace_hint: Optional[str] = None
    is_easy_apply: bool = False
    description: str = ""
    extra: dict = field(default_factory=dict)


@inject
class LinkedInJobClient:
    __di_singleton__ = True

    SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    SEARCH_PAGE_URL = "https://www.linkedin.com/jobs/search"
    DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

    def __init__(self, config_reader: ConfigReader):
        self._delay = float(config_reader.get("linkedin.request_delay_seconds", 1.1))
        self._timeout = float(config_reader.get("linkedin.timeout_seconds", 25))
        self._max_jobs = int(config_reader.get("linkedin.max_jobs_per_search", 50))
        self._posted_within_days = int(config_reader.get("linkedin.posted_within_days", 30))

    _VISA_QUERY = 'visa OR "work permit" OR sponsorship OR "blue card"'

    async def search(
        self,
        keywords: str,
        location: Optional[str] = None,
        remote_only: bool = False,
        posted_within_days: Optional[int] = None,
        max_jobs: Optional[int] = None,
        sponsorship_only: bool = False,
    ) -> List[LinkedInListing]:
        limit = min(max_jobs or self._max_jobs, 75)
        time_filter = self._time_filter(posted_within_days)
        first_tag = keywords.split(" OR ")[0].strip() if " OR " in keywords else keywords
        attempts = []
        if sponsorship_only:
            attempts.append((f"({keywords}) {self._VISA_QUERY}", location))
            if first_tag:
                attempts.append((f"{first_tag} visa sponsorship", location))
        attempts.append((keywords, location))
        if " OR " in keywords:
            attempts.append((first_tag, location))
        listings: List[LinkedInListing] = []
        async with httpx.AsyncClient(
            headers=_DEFAULT_HEADERS,
            timeout=self._timeout,
            follow_redirects=True,
        ) as client:
            for attempt in attempts:
                if attempt is None:
                    continue
                query, place = attempt
                listings = await self._collect_listings(
                    client,
                    keywords=query,
                    location=place,
                    remote_only=remote_only,
                    time_filter=time_filter,
                    limit=limit,
                )
                if listings:
                    break

            unique: dict[str, LinkedInListing] = {}
            for item in listings:
                unique.setdefault(item.linkedin_job_id, item)
            trimmed = list(unique.values())[:limit]

            detailed: List[LinkedInListing] = []
            for item in trimmed:
                try:
                    enriched = await self._fetch_detail(client, item)
                    detailed.append(enriched)
                except LinkedInUnavailableError:
                    detailed.append(item)
                await asyncio.sleep(self._delay)
            return detailed

    def _time_filter(self, posted_within_days: Optional[int]) -> str:
        days = posted_within_days if posted_within_days else self._posted_within_days
        seconds = max(1, int(days)) * 86400
        return f"r{seconds}"

    async def _collect_listings(
        self,
        client: httpx.AsyncClient,
        *,
        keywords: str,
        location: Optional[str],
        remote_only: bool,
        time_filter: str,
        limit: int,
    ) -> List[LinkedInListing]:
        listings: List[LinkedInListing] = []
        start = 0
        page_size = 25
        while len(listings) < limit:
            page = await self._fetch_search_page(
                client,
                keywords=keywords,
                location=location,
                remote_only=remote_only,
                time_filter=time_filter,
                start=start,
            )
            if not page and start == 0:
                page = await self._fetch_search_html_page(
                    client,
                    keywords=keywords,
                    location=location,
                    remote_only=remote_only,
                    time_filter=time_filter,
                )
            if not page:
                break
            listings.extend(page)
            if len(page) < 8:
                break
            start += page_size
            await asyncio.sleep(self._delay)
        return listings

    async def _fetch_search_page(
        self,
        client: httpx.AsyncClient,
        *,
        keywords: str,
        location: Optional[str],
        remote_only: bool,
        time_filter: str,
        start: int,
    ) -> List[LinkedInListing]:
        params = {
            "keywords": keywords,
            "start": start,
            "count": 25,
            "f_TPR": time_filter,
        }
        if location:
            params["location"] = location
        if remote_only:
            params["f_WT"] = "2"

        url = f"{self.SEARCH_URL}?{urlencode(params)}"
        response = await client.get(url)
        self._raise_if_blocked(response)
        if response.status_code >= 400:
            raise LinkedInUnavailableError(
                f"LinkedIn search returned HTTP {response.status_code}."
            )
        return self._parse_search_html(response.text)

    async def _fetch_search_html_page(
        self,
        client: httpx.AsyncClient,
        *,
        keywords: str,
        location: Optional[str],
        remote_only: bool,
        time_filter: str,
    ) -> List[LinkedInListing]:
        params = {
            "keywords": keywords,
            "refresh": "true",
            "f_TPR": time_filter,
        }
        if location:
            params["location"] = location
        if remote_only:
            params["f_WT"] = "2"
        response = await client.get(f"{self.SEARCH_PAGE_URL}?{urlencode(params)}")
        self._raise_if_blocked(response)
        if response.status_code >= 400:
            return []
        return self._parse_search_html(response.text)

    async def _fetch_detail(
        self, client: httpx.AsyncClient, listing: LinkedInListing
    ) -> LinkedInListing:
        url = self.DETAIL_URL.format(job_id=listing.linkedin_job_id)
        response = await client.get(url)
        self._raise_if_blocked(response)
        if response.status_code >= 400:
            return listing
        soup = BeautifulSoup(response.text, "lxml")
        description = self._text(
            soup.select_one(".show-more-less-html__markup")
            or soup.select_one(".description__text")
            or soup.select_one("[class*='description']")
        )
        salary = self._text(
            soup.select_one(".salary")
            or soup.select_one(".compensation__salary")
            or soup.select_one("[class*='salary']")
        )
        workplace = self._text(
            soup.select_one(".workplace-type")
            or soup.select_one(".description__job-criteria-text")
        )
        criteria = " ".join(
            node.get_text(" ", strip=True)
            for node in soup.select(".description__job-criteria-item")
        )
        if description:
            listing.description = description
        if salary:
            listing.salary_hint = salary
        if workplace:
            listing.workplace_hint = workplace
        if criteria:
            listing.extra["criteria"] = criteria
            listing.description = f"{listing.description}\n\n{criteria}".strip()
        easy = soup.select_one(".apply-button--easy-apply") or soup.find(
            string=re.compile(r"Easy Apply", re.I)
        )
        listing.is_easy_apply = bool(easy)
        return listing

    def _parse_search_html(self, html: str) -> List[LinkedInListing]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(
            "[data-entity-urn*='jobPosting'], "
            "[data-occludable-job-id], "
            "div.base-card, li.base-card, "
            "div.job-search-card, li.jobs-search-results__list-item"
        )
        listings: List[LinkedInListing] = []
        seen: set[str] = set()
        for card in cards:
            job_id = self._job_id_from_card(card)
            if not job_id or job_id in seen:
                continue
            seen.add(job_id)
            title = self._text(
                card.select_one("h3.base-search-card__title")
                or card.select_one(".base-search-card__title")
                or card.select_one(".job-search-card__title")
                or card.select_one("h3")
                or card.select_one("a[href*='/jobs/view/']")
            )
            company = self._text(
                card.select_one("h4.base-search-card__subtitle")
                or card.select_one(".base-search-card__subtitle")
                or card.select_one(".job-search-card__subtitle")
                or card.select_one("h4")
            )
            location = self._text(
                card.select_one(".job-search-card__location")
                or card.select_one("span.job-search-card__location")
                or card.select_one(".job-card-container__metadata-item")
            )
            posted = None
            time_node = card.select_one("time")
            if time_node is not None:
                posted = time_node.get("datetime") or time_node.get_text(strip=True)
            href = ""
            link = (
                card.select_one("a.base-card__full-link")
                or card.select_one("a[href*='/jobs/view/']")
                or card.select_one("a[href]")
            )
            if link and link.get("href"):
                href = link["href"].split("?")[0]
            salary = self._text(
                card.select_one(".job-search-card__salary-info")
                or card.select_one("[class*='salary']")
            )
            listings.append(
                LinkedInListing(
                    linkedin_job_id=job_id,
                    title=title or "Untitled role",
                    company=company,
                    location=location,
                    url=href or f"https://www.linkedin.com/jobs/view/{job_id}",
                    posted_at=posted,
                    salary_hint=salary,
                    workplace_hint=location,
                    is_easy_apply="easy apply" in card.get_text(" ", strip=True).lower(),
                )
            )
        if listings:
            return listings
        return self._parse_from_links(soup, seen)

    def _parse_from_links(self, soup: BeautifulSoup, seen: set[str]) -> List[LinkedInListing]:
        listings: List[LinkedInListing] = []
        for link in soup.select("a[href*='/jobs/view/'], a[href*='currentJobId=']"):
            href = link.get("href") or ""
            match = _JOB_ID_RE.search(href)
            if not match:
                continue
            job_id = match.group(1)
            if job_id in seen:
                continue
            seen.add(job_id)
            title = link.get_text(" ", strip=True) or "Untitled role"
            listings.append(
                LinkedInListing(
                    linkedin_job_id=job_id,
                    title=title,
                    url=href.split("?")[0] if href.startswith("http") else f"https://www.linkedin.com/jobs/view/{job_id}",
                )
            )
        return listings

    def _job_id_from_card(self, card) -> Optional[str]:
        for attr in (
            "data-entity-urn",
            "data-occludable-job-id",
            "data-job-id",
            "data-reference-id",
            "data-id",
        ):
            value = str(card.get(attr) or "")
            if value.isdigit() and len(value) >= 8:
                return value
            match = _JOB_ID_RE.search(value)
            if match:
                return match.group(1)
        link = card.select_one("a[href]")
        if link and link.get("href"):
            match = _JOB_ID_RE.search(link["href"])
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _raise_if_blocked(response: httpx.Response) -> None:
        if response.status_code in {429, 999, 403}:
            raise LinkedInUnavailableError(
                "LinkedIn blocked this search (rate limit or bot check). "
                "Wait a bit and try again from your own network."
            )

    @staticmethod
    def _text(node) -> Optional[str]:
        if node is None:
            return None
        value = node.get_text(" ", strip=True)
        return value or None
