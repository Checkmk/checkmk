#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from typing import Iterator

from tests.testlib import CMKWebSession
from tests.testlib.site import Site


def test_01_login_and_logout(site: Site):
    web = CMKWebSession(site)

    r = web.get("wato.py?mode=globalvars", allow_redirect_to_login=True)
    assert "Global settings" not in r.text

    web.login()
    web.enforce_non_localized_gui()
    r = web.get("wato.py?mode=globalvars")
    assert "Global settings" in r.text

    web.logout()
    r = web.get("wato.py?mode=globalvars", allow_redirect_to_login=True)
    assert "Global settings" not in r.text


def _get_failed_logins(site: Site, user: str) -> int:
    return int(site.read_file(f"var/check_mk/web/{user}/num_failed_logins.mk"))


def _set_failed_logins(site: Site, user: str, value: int) -> None:
    site.write_text_file(f"var/check_mk/web/{user}/num_failed_logins.mk", f"{value}\n")


@contextlib.contextmanager
def _reset_failed_logins(site: Site, username: str) -> Iterator[None]:
    assert 0 == _get_failed_logins(site, username), "initially no failed logins"
    try:
        yield
    finally:
        _set_failed_logins(site, username, 0)


def test_failed_login_counter_human(site: Site) -> None:
    """test that all authentication methods count towards the failed login attempts"""
    session = CMKWebSession(site)

    with _reset_failed_logins(site, username := "cmkadmin"):
        # Bearer token
        session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            headers={"Authorization": f"Bearer {username} wrong_password"},
            expected_code=401,
        )
        assert 1 == _get_failed_logins(site, username)

        # Login form
        session.post(
            "login.py",
            params={"_username": username, "_password": "wrong_password", "_login": "Login"},
            allow_redirect_to_login=True,
        )

        assert 2 == _get_failed_logins(site, username)


def test_failed_login_counter_automation(site: Site) -> None:
    """test that the automation user does not get locked (see Werk #15198)"""
    session = CMKWebSession(site)

    with _reset_failed_logins(site, username := "automation"):
        # Bearer token
        session.get(
            f"/{site.id}/check_mk/api/1.0/version",
            headers={"Authorization": f"Bearer {username} wrong_password"},
            expected_code=401,
        )
        assert 0 == _get_failed_logins(site, username)

        # deprecated automation login (Werk #16223)
        session.get(
            f"/{site.id}/check_mk/api/1.0/version?_username={username}&_secret=wrong_password",
            expected_code=401,
        )
        assert 0 == _get_failed_logins(site, username)
