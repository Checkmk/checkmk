#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession


@pytest.mark.skip_if_edition("saas")
def test_failed_transid_validations_is_logged(site: Site) -> None:
    web = CMKWebSession(site)
    web.login()
    site.write_file("var/log/security.log", "")
    # This page is chosen rather arbitrarily, it has only a few parameters
    # If that page changes this Test might fail and need to be adjusted
    web.get(
        f"/{site.id}/check_mk/wato.py",
        params={"_clone": "admin", "_transid": "invalid", "mode": "roles"},
    )
    assert "Transaction ID validation failed" in site.read_file("var/log/security.log")
