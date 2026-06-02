#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from scripts.html_validation.lib.sitemap import parse_gui_crawl_sitemap

CRAWL_XML = """\
<testsuites>
  <testsuite name="test-gui-crawl" tests="7" skipped="2">
    <testcase name="http://127.0.0.1:5000/mysite/check_mk/dashboard.py"/>
    <testcase name="javascript:void(0)" classname="crawled_urls">
      <skipped type="InvalidUrl" message="javascript URL"/>
    </testcase>
    <testcase name="http://127.0.0.1:5000/mysite/check_mk/static/logo.svg"/>
    <testcase name="http://127.0.0.1:5000/mysite/check_mk/static/logo.png"/>
    <testcase name="http://127.0.0.1:5000/mysite/check_mk/view.py?view_name=allhosts"/>
    <testcase name="http://127.0.0.1:5000/mysite/check_mk/view.py?view_name=svcproblems"/>
    <testcase name="data:text/html,content">
      <skipped type="InvalidUrl" message="data URL"/>
    </testcase>
  </testsuite>
</testsuites>
"""


@pytest.fixture()
def crawl_file(tmp_path: Path) -> Path:
    path = tmp_path / "crawl.xml"
    path.write_text(CRAWL_XML)
    return path


def test_parse_sitemap_returns_valid_urls(crawl_file: Path) -> None:
    urls = parse_gui_crawl_sitemap(crawl_file)
    assert urls == [
        "http://127.0.0.1:5000/mysite/check_mk/dashboard.py",
        "http://127.0.0.1:5000/mysite/check_mk/view.py?view_name=allhosts",
        "http://127.0.0.1:5000/mysite/check_mk/view.py?view_name=svcproblems",
    ]


def test_parse_sitemap_with_base_url(crawl_file: Path) -> None:
    urls = parse_gui_crawl_sitemap(crawl_file, base_url="http://localhost/v260")
    assert urls == [
        "http://localhost/v260/check_mk/dashboard.py",
        "http://localhost/v260/check_mk/view.py?view_name=allhosts",
        "http://localhost/v260/check_mk/view.py?view_name=svcproblems",
    ]
