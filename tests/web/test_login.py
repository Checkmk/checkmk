#!/usr/bin/env python
# encoding: utf-8

import pytest
from testlib import site, web

# The web fixture of testlib is doing the login automatically
def test_01_login(site, web):
    r = web.get(site.url + "wato.py")
    assert "Global Settings" in r.text


def test_02_logout(site, web):
    web.logout()

    r = web.get(site.url + "wato.py")
    assert "Global Settings" not in r.text
