from __future__ import annotations

import time
from typing import Optional, Tuple, Any, List

from bs4 import BeautifulSoup

from .. import Scraper, ScraperInput, Site
from ..utils import (
    logger,
    create_session,
)
from ...jobs import JobPost, JobResponse, Location, DescriptionFormat


class StandOutSearcher(Scraper):
    base_url = "https://www.standoutsearch.com"
    
    def __init__(self, proxies: Optional[list[str] | str] = None):
        """
        Initializes StandOutSearcher with the StandOutSearch job search URL.
        """
        super().__init__(Site.STAND_OUT_SEARCH, proxies=proxies)
        self.session = create_session(proxies=proxies)
        self.delay = 5

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        """
        Scrapes StandOutSearch for jobs with scraper_input criteria.
        :param scraper_input: Information about job search criteria.
        :return: JobResponse containing a list of jobs.
        """
        job_list: list[JobPost] = []
        page = 1

        while True:
            if len(job_list) >= scraper_input.results_wanted:
                break
            
            logger.info(f"StandOutSearch search page: {page}")
            jobs_on_page = self._find_jobs_in_page(scraper_input, page)
            if jobs_on_page:
                job_list.extend(jobs_on_page)
            else:
                break
            
            page += 1
            time.sleep(self.delay)
        
        return JobResponse(jobs=job_list[: scraper_input.results_wanted])

    def _find_jobs_in_page(self, scraper_input: ScraperInput, page: int) -> List[JobPost]:
        """
        Scrapes a page of StandOutSearch for jobs with scraper_input criteria.
        :param scraper_input: Information about job search criteria.
        :param page: Page number for pagination.
        :return: List of jobs found on page.
        """
        jobs_list = []
        url = f"{self.base_url}/jobs?page={page}"
        res = self.session.get(url)
        
        if res.status_code != 200:
            logger.error(f"Failed to fetch page {page}: {res.status_code}")
            return jobs_list
        
        soup = BeautifulSoup(res.text, 'html.parser')
        job_containers = soup.find_all('div', class_='chakra-box')  # Update with actual class
        
        for container in job_containers:
            job_post = self._process_job(container)
            if job_post:
                jobs_list.append(job_post)
        
        return jobs_list

    def _process_job(self, container: BeautifulSoup) -> Optional[JobPost]:
        """
        Processes an individual job container from the main page.
        :param container: BeautifulSoup container for the job post.
        :return: JobPost instance or None if the job is already seen.
        """
        title = container.find('p', class_='chakra-text css-134zrag').get_text(strip=True)
        company_name = container.find('p', class_='chakra-text css-14pw5qv').get_text(strip=True)
        deadline_elem = container.find('span', class_='css-111tzkx')
        deadline = deadline_elem.get_text(strip=True) if deadline_elem else None
        job_url = container.find('a', class_='chakra-link chakra-button css-19vrdtv')['href']
        
        # Fetch and parse additional details
        details_html = self.fetch_html(job_url)
        job_details = self._parse_job_details(details_html)
        
        return JobPost(
            title=title,
            company_name=company_name,
            deadline=deadline,
            job_url=job_url,
            location=job_details.location,
            address=job_details.address,
            mode=job_details.mode,
            description=job_details.description
        )

    def _parse_job_details(self, html: str) -> JobPost:
        """
        Parses detailed job information from a job-specific page.
        :param html: HTML content of the job-specific page.
        :return: JobPost instance with additional details.
        """
        soup = BeautifulSoup(html, 'html.parser')

        location_elem = soup.find('p', class_='chakra-text css-i3b6lo', text='Location:')
        location = location_elem.find_next_sibling('span').get_text(strip=True) if location_elem else None
        
        address_elem = soup.find('p', class_='chakra-text css-i3b6lo', text='Address:')
        address = address_elem.find_next_sibling('p').get_text(strip=True) if address_elem else None

        mode_elem = soup.find('p', class_='chakra-text css-i3b6lo', text='Mode:')
        mode = mode_elem.find_next_sibling('span').get_text(strip=True) if mode_elem else None

        description_elem = soup.find('p', class_='chakra-text css-i3b6lo', text='Description:')
        description = description_elem.find_next_sibling('p').get_text(strip=True) if description_elem else None

        return JobPost(
            location=location,
            address=address,
            mode=mode,
            description=description
        )
