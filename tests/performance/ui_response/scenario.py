#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""How long a page of the GUI takes to load, measured through a real browser."""

import logging
from dataclasses import dataclass
from time import time
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from playwright.sync_api import BrowserContext

from tests.performance.perftest import PerformanceTest

logger = logging.getLogger(__name__)


@dataclass
class CmkPageUrl:
    id: str
    value: str
    login: bool = True
    first_request_timeout: float = 30
    request_timeout: float = 5.0
    max_average_duration: float = 3.0
    #: Selector that has to be present before the page counts as loaded. Left unset, a page
    #: is timed to `domcontentloaded`, which is the whole story for a server-rendered page.
    #: A Vue page's content arrives in a request made *after* that event, so timing one
    #: without a selector measures its shell and misses everything that scales.
    wait_for_selector: str | None = None


def scenario_performance_ui_response(
    perftest: PerformanceTest, context: BrowserContext, page_url: CmkPageUrl
) -> None:
    """
    Scenario: UI response time.

    Sequentially issues 10 Playwright requests against the sites given page_url, appending a
    millisecond timestamp (_ts) as query parameter to avoid cache hits. Each request includes
    cache-busting headers and uses a timeout. For each request, wait for the domcontentloaded
    event being triggered.

    Args:
        context: Playwright browser context.
        page_url: Object which describes the target URL and the timeouts for each test.

    Behavior:
    - Logs a warning if a response is non-OK (non-2xx status).
    - Logs a warning if an exception occurs during the request.
    """

    first_request_duration = 0.0
    counter = 10
    page = perftest.page(perftest.central_site, context, page_url.login)
    start_time = time()
    try:
        site_url = urljoin(perftest.central_site.url, page_url.value).format_map(
            {
                "folder": "",
                "host": "dummy",
                # A page that has to address something real - a monitoring page listing
                # one host's services cannot be pointed at a host that does not exist.
                "monitored_host": perftest.monitored_host,
                "site": perftest.central_site.id,
            }
        )
        parsed_url = urlparse(site_url)
        query_params = parse_qs(parsed_url.query)

        for i in range(counter):
            query_params["_ts"] = [f"{int(time() * 1000)}"]
            new_query = urlencode(query_params, doseq=True)
            unique_url = urlunparse(parsed_url._replace(query=new_query))
            try:
                timeout_ms = 1000 * (
                    page_url.first_request_timeout if i == 0 else page_url.request_timeout
                )
                resp = page.goto(unique_url, timeout=timeout_ms, wait_until="domcontentloaded")
                if page_url.wait_for_selector is not None:
                    page.wait_for_selector(page_url.wait_for_selector, timeout=timeout_ms)
                if i == 0:
                    first_request_duration = time() - start_time
                    logger.info(
                        'UI response "%s" - first request duration: %ss',
                        page_url.id,
                        round(first_request_duration, 3),
                    )
                if resp and not resp.ok:
                    logger.warning(
                        'UI response "%s" - request %s failed with status %s (%s)',
                        page_url.id,
                        i,
                        resp.status,
                        unique_url,
                    )
            except Exception as exc:
                logger.warning(
                    'UI response "%s" - request %s raised %s (%s)',
                    page_url.id,
                    i,
                    exc,
                    unique_url,
                )
    finally:
        end_time = time()
        page.close()

    duration = end_time - start_time
    average_request_duration = (duration - first_request_duration) / (counter - 1)
    logger.info(
        'UI response "%s" - average request duration: %ss',
        page_url.id,
        round(average_request_duration, 3),
    )
    assert average_request_duration < page_url.max_average_duration
