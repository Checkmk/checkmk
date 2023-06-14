#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Generator

import pytest

from tests.testlib.crawler import Crawler, XssCrawler
from tests.testlib.site import get_site_factory, Site

logger = logging.getLogger()


@pytest.fixture(name="test_site", scope="session")
def get_site() -> Generator[Site, None, None]:
    yield from get_site_factory(prefix="crawl_").get_test_site()


@pytest.fixture(name="test_crawler", scope="session")
def crawler(test_site: Site) -> Generator[Crawler, None, None]:
    xss_crawl = os.environ.get("XSS_CRAWL", "0") == "1"
    crawler_type = XssCrawler if xss_crawl else Crawler
    test_crawler = crawler_type(test_site, report_file=os.environ.get("CRAWL_REPORT"))
    try:
        yield test_crawler
    finally:
        # teardown: creating report
        test_crawler.handle_crash_reports()
        test_crawler.report()
