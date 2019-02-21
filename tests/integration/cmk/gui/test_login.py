#!/usr/bin/env python
# encoding: utf-8

import pytest
from testlib import CMKWebSession


def test_01_login_and_logout(site):
    web = CMKWebSession(site)

    r = web.get("wato.py", allow_redirect_to_login=True)
    assert "Global Settings" not in r.text

    web.login()
    web.set_language("en")
    r = web.get("wato.py")
    assert "Global Settings" in r.text

    web.logout()
    r = web.get("wato.py", allow_redirect_to_login=True)
    assert "Global Settings" not in r.text
