#!/usr/bin/env python
# encoding: utf-8

import pytest
from testlib import site, web

# The web fixture of testlib is doing the login automatically. Check access to a page
# and then logout and check for disabled access.
def test_01_login_and_logout(site, web):
    r = web.get(site.url + "wato.py")
    assert "Global Settings" in r.text

    web.logout()
    r = web.get(site.url + "wato.py")
    assert "Global Settings" not in r.text
