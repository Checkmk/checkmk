#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import asyncio
import io
import json
import logging
import os
import re
import tarfile
import time
import traceback
from collections import deque
from collections.abc import Generator, Iterable, MutableSequence, Sequence
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from types import TracebackType
from typing import Literal, NamedTuple
from urllib.parse import parse_qs, parse_qsl, urlencode, urljoin, urlparse, urlsplit, urlunsplit

import playwright.async_api
import requests
import requests.utils
from bs4 import BeautifulSoup
from lxml import etree
from playwright.async_api import async_playwright

from tests.testlib.site import Site

logger = logging.getLogger()

CrashIdRegex = r"\w{8}-\w{4}-\w{4}-\w{4}-\w{12}"
CrashLinkRegex = rf"crash\.py\?crash_id=({CrashIdRegex})"
# We allow a 120s timeout since a very new page might take a while to setup
PW_TIMEOUT = 120_000
SkipReason = str
RelativeUrl = str


class PageContent(NamedTuple):
    content: str
    logs: Iterable[str]
    status_code: int


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

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        logger.info(
            "%d done in %.3f secs %s",
            self.done_total,
            self.duration,
            "" if exc_type is None else f"(canceled with {exc_type})",
        )
        if exc_type is not None:
            logger.error("".join(traceback.format_exception(exc_type, exc_val, exc_tb)))

    @property
    def duration(self) -> float:
        return time.time() - self.started

    def done(self, done: int) -> None:
        self.done_total += done
        if time.time() > self.next_report:
            logger.info(
                "rate: %.2f per sec (%d total)", self.done_total / self.duration, self.done_total
            )
            self.next_report = time.time() + self.report_interval


class InvalidUrl(Exception):
    def __init__(self, url: str, message: str) -> None:
        super().__init__(url, message)
        self.url = url
        self.message = message


class Url:
    def __init__(
        self,
        url: str,
        orig_url: str | None = None,
        referer_url: str | None = None,
        follow: bool = True,
    ) -> None:
        self.url = url
        self.orig_url = orig_url
        self.referer_url = referer_url
        self.follow = follow

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
class ErrorResult:
    message: str
    referer_url: str | None = None


@dataclass
class CrawlSkipInfo:
    reason: str
    message: str


@dataclass
class CrawlResult:
    duration: float = 0.0
    skipped: CrawlSkipInfo | None = None
    errors: MutableSequence[ErrorResult] = field(default_factory=list)


def format_js_error(error: playwright.async_api.Error) -> str:
    return f"{error.name}: {error.message}\n{error.stack}"


def try_find_frame_named_main(page: playwright.async_api.Page) -> playwright.async_api.Frame:
    # There are two main frames: Playwright main_frame is the outer frame, the
    # frame named main is the frame with the name "main". This is where the
    # interesting checkmk stuff is happening, so we try to find it, but fall
    # back to the outer frame if we can not find it.
    for frame in page.frames:
        if frame.name == "main":
            return frame
    return page.main_frame


class Crawler:
    def __init__(self, test_site: Site, report_file: str | None, max_urls: int = 0) -> None:
        self.duration = 0.0
        self.results: dict[str, CrawlResult] = {}
        self.site = test_site
        self.report_file = Path(report_file or self.site.result_dir) / "crawl.xml"
        self.requests_session = requests.Session()
        self._ignored_content_types: set[str] = {
            "application/json",
            "application/pdf",
            "application/x-deb",
            "application/x-debian-package",
            "application/x-gzip",
            "application/x-mkp",
            "application/x-msdos-program",
            "application/x-msi",
            "application/x-pkg",
            "application/x-redhat-package-manager",
            "application/x-rpm",
            "application/x-tar",
            "application/x-tgz",
            "application/x-yaml",
            "text/x-c++src",
            "text/x-chdr",
            "text/x-sh",
            "text/plain",
            "text/csv",
        }
        self._ignored_urls: dict[SkipReason, list[RelativeUrl]] = {}
        # limit minimum value to 0.
        self._max_urls = max(0, max_urls)
        self._todos = deque([Url(self.site.internal_url)])

    async def batch_test_urls(self, urls: Sequence[Url]) -> int:
        """
        Asynchronously tests a batch of URLs using Playwright.
        There's no parallelism within this batch, but multiple batches can be tested concurrently.
        -> see Crawler.crawl

        Args:
            urls (Sequence[Url]): A sequence of URLs to be visited and checked for errors

        Returns:
            int: The number of URLs successfully tested.
        """
        num_done = 0
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                browser_context = await self.setup_checkmk_context(browser)
                storage_state = await browser_context.storage_state()
                # makes sure authentication cookies are also available in the "requests" session.
                for cookie_dict in storage_state.get("cookies", []):
                    cookie_name = cookie_dict.get("name")
                    cookie_value = cookie_dict.get("value")
                    if cookie_name and cookie_value:
                        self.requests_session.cookies.set(name=cookie_name, value=cookie_value)
                for url in urls:
                    logger.debug("Checking URL %s", url.url)
                    num_done += await self.visit_url(browser_context, url)
            finally:
                await browser.close()
        return num_done

    async def crawl(self, max_tasks: int, max_url_batch_size: int = 100) -> None:
        """Crawl through URLs using simultaneous tasks / coroutines.

        Crawling stops when
            * no new URLs are found
            * (debug mode) at least `--max-urls` number of URLs have been crawled.
        """
        search_limited_urls: bool = self._max_urls > 0
        # special-case
        if search_limited_urls and self._max_urls < max_tasks:
            max_tasks = self._max_urls
        # ----
        with Progress() as progress:
            find_more_urls = True
            while find_more_urls:
                # body --
                # a BFS approach (graph of nodes=pages/URLs and edges=links/URLs in pages)
                #   0. the queue is Crawler._todos (deque)
                #   1. start with site URL (in __init__)
                #   2. each iteration:
                #       a. pop some batches (max_tasks*max_url_batch_size) of URLs from the queue
                #       b. for all URLs in the batches (tasks are run concurrently):
                #           visit each URL -> visit_url -> ... -> handle_new_reference
                #           handle_new_reference adds new URL(s) found in the page to the queue
                tasks: set[asyncio.Task[int]] = set()
                async with asyncio.TaskGroup() as task_group:
                    # run multiple batches of URLs concurrently (up to max_tasks),
                    # the task_group both ensures
                    #   * that all tasks are finished within the context manager
                    #   * that exceptions are collected and reported - at least here
                    for _ in range(max_tasks):
                        # get a batch of URLs to test
                        urls = [
                            self._todos.popleft() for _ in range(max_url_batch_size) if self._todos
                        ]
                        tasks.add(task_group.create_task(self.batch_test_urls(urls)))
                    logger.debug(
                        "Maximum tasks assigned. Waiting for tasks to be completed ...\n"
                        "Task group comprises of: %s",
                        " ".join(task.get_name() for task in tasks),
                    )
                # log progress of URLs visited (without skipped or erroneous URLs)
                progress.done(done=sum(task.result() for task in tasks))
                self.duration = progress.duration
                # ----

                # terminating/continuation condition
                # rationale:
                #   The queue Crawler._todos will only be repopulated
                #       * inside task_group AND
                #       * if it still has URLs
                #   (since the task_group ensures that all tasks are finished)
                #   -> we can thus check here for size of Crawler._todos
                find_more_urls = (
                    progress.done_total < self._max_urls  # (not yet reached max URLs - debug mode)
                    if search_limited_urls
                    else bool(self._todos)  # default condition: still new URLs to visit
                )
                if not find_more_urls:
                    logger.info("No more URLs to crawl. Stopping ...")
                # ----

    async def setup_checkmk_context(
        self, browser: playwright.async_api.Browser
    ) -> playwright.async_api.BrowserContext:
        context = await browser.new_context()
        context.set_default_timeout(PW_TIMEOUT)
        context.set_default_navigation_timeout(PW_TIMEOUT)
        page = await context.new_page()

        async def handle_page_error(error: playwright.async_api.Error) -> None:
            self.handle_error(
                Url(try_find_frame_named_main(page).url),
                error_type="JavascriptCreateError",
                message=format_js_error(error),
            )

        page.on("pageerror", handle_page_error)

        await page.goto(self.site.internal_url)
        await page.fill('input[name="_username"]', "cmkadmin")
        await page.fill('input[name="_password"]', "cmk")
        async with page.expect_navigation():
            await page.click("text=Login")
        await page.close()

        return context

    def _ensure_result(self, url: Url) -> None:
        if url.url not in self.results:
            self.results[url.url] = CrawlResult()

    def handle_error(self, url: Url, error_type: str, message: str = "") -> bool:
        self._ensure_result(url)
        self.results[url.url].errors.append(
            ErrorResult(referer_url=url.referer_url, message=f"{error_type}: {message}")
        )
        logger.error("page error: %s: %s, (%s)", error_type, message, url.url)
        return True

    def handle_new_reference(self, url: Url, referer_url: Url) -> bool:
        if referer_url.follow and url.url not in self.results:
            self.results[url.url] = CrawlResult()
            self._todos.append(url)
            return True
        return False

    def handle_skipped_reference(self, url: Url, reason: str, message: str) -> None:
        self._ensure_result(url)
        if self.results[url.url].skipped is None:
            self.results[url.url].skipped = CrawlSkipInfo(
                reason=reason,
                message=message,
            )

    def handle_page_done(self, url: Url, duration: float) -> bool:
        self._ensure_result(url)
        self.results[url.url].duration = duration
        logger.debug("page done in %.2f secs (%s)", duration, url.url)
        return self.results[url.url].skipped is None and len(self.results[url.url].errors) == 0

    def handle_crash_reports(self) -> None:
        crash_reports_url = urljoin(self.site.internal_url, "view.py?view_name=crash_reports")
        try:
            response = self.requests_session.get(crash_reports_url)
        except requests.RequestException as exception:
            self.handle_error(Url(url=crash_reports_url), "GetCrashReportsFailed", str(exception))
            return

        if response.status_code != 200:
            self.handle_error(
                Url(url=crash_reports_url), "CrashReportsPageFailed", str(response.status_code)
            )

        for crash_id_match in re.finditer(rf"crash_id=({CrashIdRegex})", response.text):
            self.handle_crash_report(Url("unknown url"), crash_id_match.group(1))

    def handle_crash_report(self, url: Url, crash_id: str) -> bool:
        crash_report_url = urljoin(
            self.site.internal_url,
            f"download_crash_report.py?crash_id={crash_id}&site={self.site.id}",
        )
        try:
            response = self.requests_session.get(crash_report_url)
        except requests.RequestException as exception:
            self.handle_error(
                Url(url=crash_report_url, referer_url=url.url),
                "CrashReportDownloadFailed",
                str(exception),
            )
            return False

        status_code = response.status_code
        expected_status_code = 200
        if status_code != expected_status_code:
            self.handle_error(
                Url(url=crash_report_url, referer_url=url.url),
                "CrashReportDownloadFailed",
                f"status code: {status_code}, expected: {expected_status_code}",
            )
            return False

        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
        expected_content_type = "application/x-tgz"
        if content_type != expected_content_type:
            self.handle_error(
                Url(url=crash_report_url, referer_url=url.url),
                "CrashReportDownloadFailed",
                f"content-type: {content_type}, expected: {expected_content_type}",
            )
            return False

        try:
            with tarfile.open(fileobj=io.BytesIO(response.content)) as tar:
                crash_info_file = tar.extractfile("crash.info")
                if crash_info_file is None:
                    self.handle_error(
                        Url(url=crash_report_url, referer_url=url.url),
                        "EmptyCrashReportTarFile",
                        message=crash_id,
                    )
                    return False

                crash_info = json.loads(crash_info_file.read().decode("utf-8"))
        except tarfile.ReadError:
            self.handle_error(
                Url(url=crash_report_url, referer_url=url.url),
                "InvalidCrashReportTarFile",
                repr(response.content),
            )
            return False

        # reads the crash report and dumps it indented for better readability
        crash_report = json.dumps(crash_info, indent=4)
        return self.handle_error(url, "CrashReport", message=crash_report)

    async def visit_url(
        self,
        browser_context: playwright.async_api.BrowserContext,
        url: Url,
    ) -> bool:
        """Visit a URL and check for errors.

        Args:
            browser_context: previously initiated browser context to be used
            url: URL to visit

        Returns:
            bool: True if the URL was visited successfully, False otherwise
        """
        start = time.time()
        relative_url = url.url.removeprefix(self.site.internal_url)
        if ignore_reason := next(
            (reason for reason, urls in self._ignored_urls.items() if relative_url in urls), None
        ):
            self.handle_skipped_reference(url, reason="IgnoredUrl", message=ignore_reason)
            return self.handle_page_done(url, duration=time.time() - start)
        content_type = (
            self.requests_session.head(url.url)
            .headers.get("content-type", "")
            .split(";", 1)[0]
            .strip()
        )
        if content_type == "text/html" or content_type.startswith("image/"):
            try:
                page_content = await self.get_page_content(browser_context, url)
                if page_content.status_code == 404:
                    self.handle_error(
                        url, error_type="NotFound", message=f"{content_type} resource not found"
                    )
                else:
                    await self.validate(url, page_content.content, page_content.logs)
            except playwright.async_api.Error as e:
                self.handle_error(url, "BrowserError", repr(e))
        elif content_type in self._ignored_content_types:
            self.handle_skipped_reference(url, reason="IgnoredContentType", message=content_type)
        else:
            self.handle_error(url, error_type="UnknownContentType", message=content_type)

        return self.handle_page_done(url, duration=time.time() - start)

    @staticmethod
    async def get_page_content(
        browser_context: playwright.async_api.BrowserContext,
        url: Url,
    ) -> PageContent:
        logs = []

        async def handle_console_messages(msg: playwright.async_api.ConsoleMessage) -> None:
            location = (
                f"{msg.location['url']}:{msg.location['lineNumber']}:{msg.location['columnNumber']}"
            )
            logs.append(f"{msg.type}: {msg.text} ({location})")

        async def handle_page_error(error: playwright.async_api.Error) -> None:
            logs.append(format_js_error(error))

        page = await browser_context.new_page()
        page.on("pageerror", handle_page_error)
        page.on("console", handle_console_messages)
        try:
            response = await page.goto(url.url)
            return PageContent(
                content=await page.content(),
                logs=logs,
                status_code=response.status if response else 0,
            )
        finally:
            await page.close()

    async def validate(self, url: Url, text: str, logs: Iterable[str]) -> None:
        def blocking() -> None:
            soup = BeautifulSoup(text, "lxml")
            self.check_content(url, soup)
            self.check_links(url, soup)
            self.check_frames(url, soup)
            self.check_iframes(url, soup)
            self.check_images(url, soup)
            self.check_logs(url, logs)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, blocking)

    def check_content(self, url: Url, soup: BeautifulSoup) -> None:
        if soup.find("div", id="login") is not None:
            self.handle_error(url, "LoginError", "login requested")

        ignore_texts = [
            "This view can only be used in mobile mode.",
            # Some single context views are accessed without their context information, which
            # results in a helpful error message since 1.7. These are not failures that this test
            # should report.
            "Missing context information",
            # Same for availability views that cannot be accessed anymore
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
            if not any(ignore_text in inner_html for ignore_text in ignore_texts):
                self.handle_error(url, "HtmlError", f"Found error: {inner_html}")

    def check_frames(self, url: Url, soup: BeautifulSoup) -> None:
        self.check_referenced(url, soup, "frame", "src")

    def check_iframes(self, url: Url, soup: BeautifulSoup) -> None:
        self.check_referenced(url, soup, "iframe", "src")

    def check_images(self, url: Url, soup: BeautifulSoup) -> None:
        self.check_referenced(url, soup, "img", "src")

    def check_links(self, url: Url, soup: BeautifulSoup) -> None:
        self.check_referenced(url, soup, "a", "href")

    def check_referenced(
        self,
        referer_url: Url,
        soup: BeautifulSoup,
        tag_name: Literal["frame", "iframe", "img", "a"],
        attr_name: Literal["src", "href"],
    ) -> None:
        elements = soup.find_all(tag_name)
        for element in elements:
            if not (orig_url := str(element.get(attr_name, ""))):
                continue  # Skip elements that don't have the attribute in question
            if not (normalized_orig_url := self.normalize_url(orig_url)):
                continue
            url = Url(normalized_orig_url, orig_url=orig_url, referer_url=referer_url.url)
            try:
                self.verify_is_valid_url(url.url)
            except InvalidUrl as invalid_url:
                self.handle_skipped_reference(url, reason="InvalidUrl", message=invalid_url.message)
            else:
                self.handle_new_reference(url, referer_url=referer_url)

    def check_logs(self, url: Url, logs: Iterable[str]) -> None:
        accepted_logs = [
            "Missing object for SimpleBar initiation.",
        ]
        for log in logs:
            if not any(accepted_log in log for accepted_log in accepted_logs):
                self.handle_error(url, error_type="JavascriptError", message=log)

    def verify_is_valid_url(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme == "javascript":
            raise InvalidUrl(url, "javascript URL")

        # skip external urls
        if url.startswith("http") and not url.startswith(self.site.url_prefix):
            raise InvalidUrl(url, "external url")
        # skip non check_mk urls
        if (
            not parsed.path.startswith(f"/{self.site.id}/check_mk")
            or "../pnp4nagios/" in parsed.path
            or "../nagvis/" in parsed.path
            or "check_mk/plugin-api" in parsed.path
            or "../nagios/" in parsed.path
        ):
            raise InvalidUrl(url, "non Check_MK URL")

        file_name = os.path.basename(parsed.path)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))

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
        if parsed.path.startswith(f"/{self.site.id}/check_mk/agents/"):
            raise InvalidUrl(url, "agent download file")

        # Skip combined graph pages which take way too long for our crawler with unrestricted
        # contexts. These pages take >10 seconds to load while crawling
        if file_name == "combined_graphs.py" and not query.get("host"):
            raise InvalidUrl(url, "combined graph with unrestricted context")

        # From the list visuals page (e.g. edit_views.py) there are links with explicit "owner="
        # query string. These parameters are useful for admins, in case they want to display the
        # view of a specific user. In our crawl scenario this results in all view related pages
        # (regular view, availability sub-views, reports and so on) being crawled twice. To reduce
        # the number of URLs being crawled, we exclude the view.py with empty "owner" parameter.
        if file_name == "view.py" and query.get("owner") == "":
            raise InvalidUrl(url, "explicit empty owner (redundant view)")

        # Do not crawl the thousands of werk pages. Visit at least some of them to be able to catch
        # some general rendering issues.
        if file_name == "werk.py" and query.get("werk") not in [
            "11363",
            "5605",
            "12908",
            "12389",
            "7352",
            "11361",
            "12149",
            "5744",
            "8350",
            "6240",
            "5958",
        ]:
            raise InvalidUrl(url, "Skip werk pages")

    def normalize_url(self, url: str) -> str:
        url = urljoin(self.site.internal_url, url.rstrip("#"))
        parsed = list(urlsplit(url))
        parsed[3] = urlencode(sorted(parse_qsl(parsed[3], keep_blank_values=True)))
        return urlunsplit(parsed)

    def report(self) -> None:
        self.site.save_results()
        self._write_report_file()

        error_messages = list(
            chain.from_iterable(
                (
                    [
                        f"[{url} - found on {error.referer_url}] {error.message}"
                        for error in result.errors
                    ]
                    for url, result in self.results.items()
                    if result.errors
                )
            )
        )
        if error_messages:
            joined_error_messages = "\n".join(error_messages)
            raise Exception(
                f"Crawled {len(self.results)} URLs in {self.duration} seconds. Failures:\n{joined_error_messages}"
            )

    def _write_report_file(self) -> None:
        root = etree.Element("testsuites")
        testsuite = etree.SubElement(root, "testsuite")

        tests, errors, skipped = 0, 0, 0
        for url, result in self.results.items():
            testcase = etree.SubElement(
                testsuite,
                "testcase",
                attrib={
                    "name": url,
                    "classname": "crawled_urls",
                    "time": f"{result.duration:.3f}",
                },
            )
            if result.skipped is not None:
                skipped += 1
                etree.SubElement(
                    testcase,
                    "skipped",
                    attrib={
                        "type": result.skipped.reason,
                        "message": result.skipped.message,
                    },
                )
            elif result.errors:
                errors += 1
                for error in result.errors:
                    failure = etree.SubElement(
                        testcase, "failure", attrib={"message": error.message}
                    )
                    failure.text = f"referer_url: {error.referer_url}"

            tests += 1

        testsuite.attrib["name"] = "test-gui-crawl"
        testsuite.attrib["tests"] = str(tests)
        testsuite.attrib["skipped"] = str(skipped)
        testsuite.attrib["errors"] = str(errors)
        testsuite.attrib["failures"] = "0"
        testsuite.attrib["time"] = f"{self.duration:.3f}"
        testsuite.attrib["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        self.report_file.write_bytes(etree.tostring(root, pretty_print=True))


class XssCrawler(Crawler):
    Payload = """javascript:/*--></title></style></textarea></script></xmp><svg/onload='+/"/+/onmouseover=1/+/[*/[]/+console.log("XSS vulnerability")//'>"""

    def handle_error(self, url: Url, error_type: str, message: str = "") -> bool:
        if error_type == "HtmlError":
            return False
        if error_type == "UnknownContentType" and message == "application/problem+json":
            return False
        return super().handle_error(url, error_type, message)

    def handle_page_done(self, url: Url, duration: float) -> bool:
        if super().handle_page_done(url, duration):
            for mutated_url in mutate_url_with_xss_payload(url, self.Payload):
                super().handle_new_reference(mutated_url, url)
            return True
        return False


def mutate_url_with_xss_payload(url: Url, payload: str) -> Generator[Url]:
    """For each query parameter in `url`, produce a URL where that parameter is set to `payload`

    >>> urls = mutate_url_with_xss_payload(Url("example.com?foo=bar&empty="), "PAYLOAD")
    >>> next(urls).url
    'example.com?foo=PAYLOAD&empty='
    >>> next(urls).url
    'example.com?foo=bar&empty=PAYLOAD'

    (Be aware that this doctest is not run.)
    """
    parsed_url = urlparse(url.url)
    parsed_query = parse_qs(parsed_url.query, keep_blank_values=True)
    for key, values in parsed_query.items():
        for change_idx in range(len(values)):
            mutated_values = [
                payload if idx == change_idx else value for idx, value in enumerate(values)
            ]
            mutated_query = {**parsed_query, key: mutated_values}
            mutated_url = parsed_url._replace(query=urlencode(mutated_query, doseq=True))
            yield Url(
                url=mutated_url.geturl(),
                referer_url=url.referer_url,
                orig_url=url.orig_url,
                follow=False,
            )
