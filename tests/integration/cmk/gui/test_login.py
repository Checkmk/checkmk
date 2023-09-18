#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import CMKWebSession
from tests.testlib.site import Site


def test_01_login_and_logout(site: Site) -> None:
    web = CMKWebSession(site)

    r = web.get("wato.py?mode=globalvars", allow_redirect_to_login=True)
    assert "Global settings" not in r.text

    web.login()
    site.enforce_non_localized_gui(web)
    r = web.get("wato.py?mode=globalvars")
    assert "Global settings" in r.text

    web.logout()
    r = web.get("wato.py?mode=globalvars", allow_redirect_to_login=True)
    assert "Global settings" not in r.text


def test_session_cookie(site: Site) -> None:
    web = CMKWebSession(site)

    web.login()
    for cookie in web.session.cookies:
        if not cookie.name == f"auth_{site.id}":
            continue
        assert cookie.path == f"/{site.id}/"
        # This is ugly but IMHO the only way...
        assert "HttpOnly" in cookie.__dict__.get("_rest", {})
        assert cookie.__dict__.get("_rest", {}).get("SameSite") == "Lax"
