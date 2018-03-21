#!/usr/bin/env python

import cmk.werks

def test_load(site):
    werks = cmk.werks.load()
    assert len(werks) > 1000


def test_regular_werks(site):
    werks = cmk.werks.load()

    regular_werks = [ id for id in werks.keys() if id < 7500 ]
    assert len(regular_werks) > 1000


def test_enterprise_werks(site):
    werks = cmk.werks.load()

    enterprise_werks = [ id for id in werks.keys() if id >= 8000 ]

    if site.version.edition() == "raw":
        assert not enterprise_werks
    else:
        assert enterprise_werks


def test_cmk_omd_werks(site):
    werks = cmk.werks.load()

    cmk_omd_werks = [ id for id in werks.keys() if id >= 7500 and id < 8000 ]
    assert cmk_omd_werks
