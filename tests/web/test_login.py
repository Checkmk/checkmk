#!/usr/bin/env python
# encoding: utf-8

import pytest
from testlib import WebSession

def test_01_login_and_logout(site):
    web = WebSession(site)

    r = web.get(site.url + "wato.py")
    assert "Global Settings" not in r.text

    web.login()
    web.set_language("en")
    r = web.get(site.url + "wato.py")
    assert "Global Settings" in r.text

    web.logout()
    r = web.get(site.url + "wato.py")
    assert "Global Settings" not in r.text
