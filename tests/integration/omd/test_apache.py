#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import uuid

import pytest
import requests

from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession


def test_http_methods(site: Site) -> None:
    """Check that some methods are forbidden and the denial is logged

    ASVS: V14.5.1"""

    user_agent = str(uuid.uuid4())
    response = requests.request(
        "PROPFIND", site.internal_url, timeout=5, headers={"User-Agent": user_agent}
    )
    assert response.status_code == 405

    apache_log_file = site.read_file("var/log/apache/access_log")
    for line in apache_log_file.splitlines():
        if re.match(r'^.*"PROPFIND /\w+/check_mk/ HTTP/1.1" 405 \d+ "-" "' + user_agent, line):
            return
    pytest.fail("Could not find regex in logfile")


@pytest.mark.parametrize(
    ["size", "status_code"],
    [
        pytest.param(1024 * 1024 * (100 - 1), 200, id="under_limit"),
        pytest.param(1024 * 1024 * 100, 413, id="at_limit"),
        pytest.param(1024 * 1024 * (100 * 10), 413, id="over_limit"),
    ],
)
def test_upload_limit(site: Site, web: CMKWebSession, size: int, status_code: int) -> None:
    """
    Check that the 100MB file size limit is enforced.
    """

    file = "a" * size
    web.post(
        f"/{site.id}/check_mk/wato.py",
        files={"any_file": file},
        expected_code=status_code,
    )
