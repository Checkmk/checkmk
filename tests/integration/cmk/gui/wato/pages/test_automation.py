#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from ast import literal_eval

import pytest

from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession

pytestmark = [pytest.mark.skip_if_edition("saas")]


def _distributed_site_secret(site: Site) -> str:
    _path = "var/check_mk/wato/automation_secret.mk"
    if site.file_exists(_path):
        return literal_eval(site.read_file(_path))

    web = CMKWebSession(site)
    web.login()
    r = web.get(
        "automation_login.py",
        params={
            "_version": f"{site.version.branch_version}p1337",
            "_edition_short": site.edition.short,
        },
    )
    return literal_eval(r.text)["login_secret"]


def test_central_site_version_is_stored(site: Site) -> None:
    """With Werk #### we need to store information about the central site in order to figure out
    what authentication scheme to use, here I want to make sure this works"""

    site.delete_file("var/check_mk/central_site_info.json")
    web = CMKWebSession(site)

    web.post(
        "automation.py",
        data={
            "secret": _distributed_site_secret(site),
            "command": "ping",
            "_version": f"{site.version.branch_version}p1337",
            "_edition_short": site.edition.short,
        },
    )

    assert (
        site.read_file("var/check_mk/last_known_site_version.json")
        == f'{{"version_str":"{site.version.branch_version}p1337"}}'
    )


def test_wrong_central_site_version(site: Site) -> None:
    """Make sure that a malformed version does not make it to disk"""

    site.delete_file("var/check_mk/last_known_site_version.json")
    web = CMKWebSession(site)

    r = web.post(
        "automation.py",
        data={
            "secret": _distributed_site_secret(site),
            "command": "ping",
            "_version": "foobar",
            "_edition_short": site.edition.short,
        },
    )
    assert r.text == "Invalid version string &quot;foobar&quot;"
    assert not site.file_exists("var/check_mk/last_known_site_version.json")
