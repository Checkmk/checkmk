#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Generator

import pytest

from tests.testlib.crawler import Crawler, XssCrawler
from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import current_base_branch_name

logger = logging.getLogger()


@pytest.fixture(name="test_site", scope="session", autouse=True)
def get_site() -> Site:
    reuse = os.environ.get("REUSE")
    # if REUSE is undefined, a site will neither be reused nor be dropped
    reuse_site = reuse == "1"
    drop_site = reuse == "0"
    sf = get_site_factory(
        prefix="crawl_",
        install_test_python_modules=False,
        fallback_branch=current_base_branch_name,
    )

    site = sf.get_existing_site("central")
    if site.exists() and reuse_site:
        logger.info("Reuse existing site (REUSE=1)")
        site = sf.get_existing_site("central")
    else:
        if site.exists() and drop_site:
            logger.info("Dropping existing site (REUSE=0)")
            site.rm()
        logger.info("Creating new site")
        site = sf.get_site("central")
    logger.info("Site %s is ready!", site.id)

    return site


@pytest.fixture(name="test_crawler", scope="session", autouse=True)
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
