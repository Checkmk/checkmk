#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from queue import Empty, Queue
from typing import Dict, List, Optional, TypedDict
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import pytest
from bs4 import BeautifulSoup  # type: ignore[import]
from lxml import etree  # type: ignore[import]

from tests.testlib.site import get_site_factory, Site
from tests.testlib.version import CMKVersion
from tests.testlib.web_session import CMKWebSession

logger = logging.getLogger()


class InvalidUrl(Exception):
    def __init__(self, url: str, message: str) -> None:
        super().__init__(url, message)
        self.url = url
        self.message = message


class Url:
    def __init__(self,
                 url: str,
                 orig_url: Optional[str] = None,
                 referer_url: Optional[str] = None) -> None:
        self.url = url
        self.orig_url = orig_url
        self.referer_url = referer_url

    def __hash__(self) -> int:
        return hash(self.url)

    # Strip host and site prefix
    def neutral_url(self) -> str:
        return "check_mk/" + self.url.split("/check_mk/", 1)[1]

    # Strip proto and host
    def url_without_host(self) -> str:
        parsed = list(urlsplit(self.url))
        parsed[0] = ""
        parsed[1] = ""
        return urlunsplit(parsed)


@dataclass
class PageEvent:
    url: Url

    def __hash__(self):
        return hash(self.url)


@dataclass
class ReferenceFound(PageEvent):
    pass


@dataclass
class PageError(PageEvent):
    message: str


@dataclass
class SkipReference(PageEvent):
    reason: str
    message: str


@dataclass
class PageStatistic(PageEvent):
    duration: float


class IterableQueue(Queue):
    def __iter__(self) -> "IterableQueue":
        return self

    def __next__(self):
        try:
            return self.get_nowait()
        except Empty:
            raise StopIteration()


class PageValidator:
    def __init__(self, event_queue: Queue, site_id: str, base_url: str) -> None:
        self.site_id = site_id
        self.base_url = base_url
        self.event_queue = event_queue

    def validate(self, url: Url, text: str) -> None:
        soup = BeautifulSoup(text, "lxml")
        self.check_content(url, soup)
        self.check_links(url, soup)
        self.check_frames(url, soup)
        self.check_iframes(url, soup)

    def check_content(self, url: Url, soup: BeautifulSoup) -> None:
        ignore_texts = [
            "This view can only be used in mobile mode.",
            # Some single context views are accessed without their context information, which
            # results in a helpful error message since 1.7. These are not failures that this test
            # should report.
            "Missing context information",
            # Same for availability views that cannot be accessed any more
            # from views with missing context
            "miss some required context information",
            # Same for dashlets that are related to a specific context
            "There are no metrics meeting your context filters",
            # Some of the errors are only visible to the user when trying to submit and
            # some are visible for the reason that the GUI crawl sites do not have license
            # information configured -> ignore the errors
            "license usage report",
        ]
        for element in soup.select("div.error"):
            inner_html = str(element)
            if not any((ignore_text in inner_html for ignore_text in ignore_texts)):
                self.event_queue.put(PageError(url, f"Found error: {inner_html}"))

    def check_frames(self, url: Url, soup: BeautifulSoup) -> None:
        self.check_referenced(url, soup, "frame", "src")

    def check_iframes(self, url: Url, soup: BeautifulSoup) -> None:
        self.check_referenced(url, soup, "iframe", "src")

    def check_links(self, url: Url, soup: BeautifulSoup) -> None:
        self.check_referenced(url, soup, "a", "href")

    def check_referenced(self, referer_url: Url, soup: BeautifulSoup, tag: str, attr: str) -> None:
        elements = soup.find_all(tag)
        for element in elements:
            orig_url = element.get(attr)
            if orig_url is None:
                continue  # Skip elements that don't have the attribute in question
            normalized_orig_url = self.normalize_url(orig_url)
            if normalized_orig_url is None:
                continue
            url = Url(normalized_orig_url, orig_url=orig_url, referer_url=referer_url.url)
            try:
                self.verify_is_valid_url(url.url)
            except InvalidUrl as invalid_url:
                self.event_queue.put(
                    SkipReference(url, reason="invalid-url", message=invalid_url.message))
            else:
                self.event_queue.put(ReferenceFound(url))

    def verify_is_valid_url(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "http":
            raise InvalidUrl(url, f"invalid scheme: {parsed.scheme}")
        # skip external urls
        if url.startswith("http://") and not url.startswith(self.base_url):
            raise InvalidUrl(url, "external url")
        # skip non check_mk urls
        if not parsed.path.startswith(f"/{self.site_id}/check_mk") \
           or "../pnp4nagios/" in parsed.path \
           or "../nagvis/" in parsed.path \
           or "check_mk/plugin-api" in parsed.path \
           or "../nagios/" in parsed.path:
            raise InvalidUrl(url, "non Check_MK URL")
        # skip current url with link to index
        if "index.py?start_url=" in url:
            raise InvalidUrl(url, "link to index with current URL")
        if "logout.py" in url:
            raise InvalidUrl(url, "logout URL")
        if "_transid=" in url:
            raise InvalidUrl(url, "action URL")
        if "selection=" in url:
            raise InvalidUrl(url, "selection URL")
        # TODO: Remove this exclude when ModeCheckManPage works without an
        # automation call. Currently we have to use such a call to enrich the
        # man page with some additional info from config.check_info, see
        # AutomationGetCheckManPage.
        if "mode=check_manpage" in url and "wato.py" in url:
            raise InvalidUrl(url, "man page URL")
        # Don't follow filled in filter form views
        if "view.py" in url and "filled_in=filter" in url:
            raise InvalidUrl(url, "filled in filter URL")
        # Don't follow the view editor
        if "edit_view.py" in url:
            raise InvalidUrl(url, "view editor URL")
        # Skip agent download files
        if parsed.path.startswith(f"/{self.site_id}/check_mk/agents/"):
            raise InvalidUrl(url, "agent download file")

    def normalize_url(self, url: str) -> str:
        url = urljoin(self.base_url, url.rstrip("#"))
        parsed = list(urlsplit(url))
        parsed[3] = urlencode(sorted(parse_qsl(parsed[3], keep_blank_values=True)))
        return urlunsplit(parsed)


class PageVisitor:
    def __init__(self, site: Site) -> None:
        self.site = site

        self.web_session = CMKWebSession(site)
        # disable content parsing on each request for performance reasons
        self.web_session._handle_http_response = lambda *args, **kwargs: None  # type: ignore
        self.web_session.login()
        self.web_session.enforce_non_localized_gui()

    async def visit_url(self, url: Url, event_queue: Queue) -> None:
        start = time.time()
        content_type = await self.get_content_type(url)
        if content_type.startswith("text/html"):
            text = await self.get_text(url)
            await self.validate(url, text, event_queue)
        elif any((content_type.startswith(ignored_start)
                  for ignored_start in ["text/plain", "text/csv"])):
            event_queue.put(SkipReference(url, reason="content-type", message=content_type))
        elif content_type in [
                "application/x-rpm",
                "application/x-deb",
                "application/x-debian-package",
                "application/x-gzip",
                "application/x-msdos-program",
                "application/x-msi",
                "application/x-tgz",
                "application/x-redhat-package-manager",
                "application/x-pkg",
                "application/x-tar",
                "application/json",
                "application/pdf",
                "image/png",
                "image/gif"
                "text/x-chdr",
                "text/x-c++src",
                "text/x-sh",
        ]:
            event_queue.put(SkipReference(url, reason="content-type", message=content_type))
        else:
            event_queue.put(PageError(url, f"Unknown content type {content_type}"))

        event_queue.put(PageStatistic(url=url, duration=time.time() - start))

    async def get_content_type(self, url: Url) -> str:
        def blocking():
            response = self.web_session.request("head", url.url_without_host())
            return response.headers.get('content-type')

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, blocking)

    async def get_text(self, url: Url) -> str:
        def blocking():
            response = self.web_session.get(url.url_without_host())
            return response.text

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, blocking)

    async def validate(self, url: Url, text: str, event_queue: Queue) -> None:
        def blocking():
            validator = PageValidator(event_queue, self.site.id, self.site.internal_url)
            validator.validate(url, text)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, blocking)


class Progress:
    def __init__(self, report_interval: float = 10) -> None:
        self.started = time.time()
        self.done_total = 0
        self.report_interval = report_interval
        self.next_report = 0.0

    def __enter__(self) -> "Progress":
        self.started = time.time()
        self.next_report = self.started + self.report_interval
        self.done_total = 0
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.info("%d done in %.3f secs", self.done, self.duration)

    @property
    def duration(self) -> float:
        return time.time() - self.started

    def done(self, done: int) -> None:
        self.done_total += done
        if time.time() > self.next_report:
            logger.info("rate: %.2f per sec", self.done_total / self.duration)
            self.next_report = time.time() + self.report_interval


class CrawlError(TypedDict):
    referer_url: Optional[str]
    message: str


class CrawlSkipInfo(TypedDict):
    reason: str
    message: str


class CrawlResult(TypedDict, total=False):
    duration: float
    skipped: CrawlSkipInfo
    errors: List[CrawlError]


class Crawler:
    def __init__(self, site: Site):
        self.duration = 0.0
        self.results: Dict[str, CrawlResult] = {}
        self.site = site
        self.num_workers = 10

    def report_file(self) -> str:
        return os.environ.get("CRAWL_REPORT", "") or self.site.result_dir() + "/crawl.xml"

    def report(self) -> None:
        self.site.save_results()
        self._write_report_file()

        error_messages = list(
            chain.from_iterable(([
                f"[{url} - found on {error['referer_url']}] {error['message']}"
                for error in result["errors"]
            ]
                                 for url, result in self.results.items()
                                 if "errors" in result)))
        if error_messages:
            joined_error_messages = '\n'.join(error_messages)
            raise Exception(
                f"Crawled {len(self.results)} URLs in {self.duration} seconds. Failures:\n{joined_error_messages}"
            )

    def _write_report_file(self) -> None:
        root = etree.Element("testsuites")
        testsuite = etree.SubElement(root, "testsuite")

        tests, errors, skipped = 0, 0, 0
        for url, result in self.results.items():
            testcase = etree.SubElement(testsuite,
                                        "testcase",
                                        attrib={
                                            "name": url,
                                            "classname": "crawled_urls",
                                            "time": f"{result.get('duration', 0.0):.3f}",
                                        })
            if "skipped" in result:
                skipped += 1
                skip_info = result["skipped"]
                etree.SubElement(testcase,
                                 "skipped",
                                 attrib={
                                     "type": skip_info["reason"],
                                     "message": skip_info["message"],
                                 })
            elif result.get("errors", None):
                errors += 1
                for error in result["errors"]:
                    failure = etree.SubElement(testcase,
                                               "failure",
                                               attrib={"message": error["message"]})
                    failure.text = f'referer_url: {error["referer_url"]}'

            tests += 1

        testsuite.attrib["name"] = "test-gui-crawl"
        testsuite.attrib["tests"] = str(tests)
        testsuite.attrib["skipped"] = str(skipped)
        testsuite.attrib["errors"] = str(errors)
        testsuite.attrib["failures"] = "0"
        testsuite.attrib["time"] = f"{self.duration:.3f}"
        testsuite.attrib["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        Path(self.report_file()).write_bytes(etree.tostring(root, pretty_print=True))

    async def crawl(self) -> None:
        with Progress() as progress:
            event_queue = IterableQueue()
            visitor = PageVisitor(self.site)
            tasks = {
                asyncio.create_task(visitor.visit_url(Url(self.site.internal_url), event_queue))
            }
            while tasks or not event_queue.empty():
                done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for event in event_queue:
                    if isinstance(event, ReferenceFound):
                        if event.url.url not in self.results:
                            self.results[event.url.url] = CrawlResult()
                            tasks.add(asyncio.create_task(visitor.visit_url(event.url,
                                                                            event_queue)))
                    elif isinstance(event, PageError):
                        self.results[event.url.url].setdefault("errors", []).append({
                            "referer_url": event.url.referer_url,
                            "message": event.message
                        })
                    elif isinstance(event, SkipReference):
                        self.results.setdefault(event.url.url, CrawlResult())["skipped"] = {
                            "reason": event.reason,
                            "message": event.message,
                        }
                    elif isinstance(event, PageStatistic):
                        self.results.setdefault(event.url.url,
                                                CrawlResult())["duration"] = event.duration
                    else:
                        raise RuntimeError(f"unkown event: {type(event)}")

                progress.done(len(done))
                self.duration = progress.duration


@pytest.fixture
def site() -> Site:
    version = os.environ.get("VERSION", CMKVersion.DAILY)
    sf = get_site_factory(prefix="crawl_",
                          update_from_git=version == "git",
                          install_test_python_modules=False)

    site = None
    if os.environ.get("REUSE", 0) == "1":
        site = sf.get_existing_site("central")
    if site is None or not site.exists():
        site = sf.get_site("central")
    logger.info("Site %s is ready!", site.id)

    return site


def test_crawl(site) -> None:
    crawler = Crawler(site)
    try:
        asyncio.run(crawler.crawl())
    finally:
        crawler.report()
