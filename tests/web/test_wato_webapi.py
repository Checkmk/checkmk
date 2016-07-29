#!/usr/bin/env python
# encoding: utf-8

import pytest
from testlib import site, web

def test_01_global_settings(site, web):
    r = web.get(site.url + "wato.py")
    assert "Global Settings" in r.text


def test_02_add_host(web):
    web.add_host("test-host", attributes={
        "ipaddress": "127.0.0.1",
    })
