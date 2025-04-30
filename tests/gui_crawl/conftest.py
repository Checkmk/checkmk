#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Generator

import pytest

from tests.gui_crawl.crawler import Crawler, XssCrawler

from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.site import get_site_factory, Site

logger = logging.getLogger()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--max-urls",
        action="store",
        default=int(os.environ.get("GUI_CRAWLER_URL_LIMIT", "0")),
        type=int,
        help="Select only N URLs for the crawler tests (0=all).",
    )


@pytest.fixture(name="test_site", scope="session")
def get_site(request: pytest.FixtureRequest) -> Generator[Site, None, None]:
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        yield from get_site_factory(prefix="crawl_").get_test_site()


@pytest.fixture(name="test_crawler", scope="session")
def crawler(test_site: Site, pytestconfig: pytest.Config) -> Generator[Crawler, None, None]:
    xss_crawl = os.environ.get("XSS_CRAWL", "0") == "1"
    crawler_type = XssCrawler if xss_crawl else Crawler
    test_crawler = crawler_type(
        test_site,
        report_file=os.environ.get("CRAWL_REPORT"),
        max_urls=pytestconfig.getoption(name="--max-urls"),
    )
    try:
        yield test_crawler
    finally:
        # teardown: creating report
        test_crawler.handle_crash_reports()
        test_crawler.report()
