#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.pytest_helpers.marks import skip_if_saas_edition
from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession


@skip_if_saas_edition
def test_failed_transid_validations_is_logged(site: Site) -> None:
    web = CMKWebSession(site)
    web.login()
    site.write_text_file("var/log/security.log", "")
    # This page is chosen rather arbitrarily, it has only a few parameters
    # If that page changes this Test might fail and need to be adjusted
    web.get(
        f"/{site.id}/check_mk/wato.py",
        params={"_clone": "admin", "_transid": "invalid", "mode": "roles"},
    )
    assert "Transaction ID validation failed" in site.read_file("var/log/security.log")
