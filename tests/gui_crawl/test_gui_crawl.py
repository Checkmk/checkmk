#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import os
from collections.abc import Iterable

import pytest

from tests.gui_crawl.crawler import Crawler, mutate_url_with_xss_payload, Url


def test_crawl(test_crawler: Crawler) -> None:
    asyncio.run(test_crawler.crawl(max_tasks=int(os.environ.get("GUI_CRAWLER_TASK_LIMIT", "7"))))


@pytest.mark.type("unit")
@pytest.mark.parametrize(
    "url,payload,expected_urls",
    [
        ("http://host/page.py", "payload", []),
        ("http://host/page.py?key=", "payload", ["http://host/page.py?key=payload"]),
        ("http://host/page.py?key=value", "payload", ["http://host/page.py?key=payload"]),
        (
            "http://host/page.py?k1=v1&k2=v2",
            "payload",
            ["http://host/page.py?k1=payload&k2=v2", "http://host/page.py?k1=v1&k2=payload"],
        ),
        (
            "http://host/page.py?k1=v1&k1=v2",
            "payload",
            ["http://host/page.py?k1=payload&k1=v2", "http://host/page.py?k1=v1&k1=payload"],
        ),
    ],
)
def test_mutate_url_with_xss_payload(url: str, payload: str, expected_urls: Iterable[str]) -> None:
    assert [u.url for u in mutate_url_with_xss_payload(Url(url), payload)] == expected_urls


@pytest.mark.type("unit")
def test_mutate_url_with_xss_payload_url_metadata() -> None:
    url = Url(
        url="http://host/page.py?key=value",
        referer_url="http://host/referer.py",
        orig_url="http://host/orig.py",
    )
    mutated_url = list(mutate_url_with_xss_payload(url, "payload")).pop(0)
    assert mutated_url.referer_url == url.referer_url
    assert mutated_url.orig_url == url.orig_url
    assert not mutated_url.follow
