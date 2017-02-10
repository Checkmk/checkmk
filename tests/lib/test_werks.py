#!/usr/bin/env python

import os

import testlib
import cmk.werks

def test_load():
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


# TODO: cmk omd werks are currently missing
#def test_cmk_omd_werks(site):
#    werks = cmk.werks.load()
#
#    cmk_omd_werks = [ id for id in werks.keys() if id >= 7500 and id < 8000 ]
#    assert cmk_omd_werks

def test_write_precompiled_werks(tmpdir, site, monkeypatch):
    tmp_dir = "%s" % tmpdir

    cmk_werks = cmk.werks.load_raw_files(os.path.join(testlib.cmk_path(), ".werks"))
    assert len(cmk_werks) > 1000
    assert [ w for w in cmk_werks.keys() if w >= 7500 ] == []

    cmk.werks.write_precompiled_werks(os.path.join(tmp_dir, "werks"), cmk_werks)

    if site.version.edition() == "raw":
        cmc_werks = cmk.werks.load_raw_files(os.path.join(testlib.cmc_path(), ".werks"))
        assert len(cmc_werks) > 1000
        assert [ w for w in cmc_werks.keys() if  w < 8000 ] == []

        cmk.werks.write_precompiled_werks(os.path.join(tmp_dir, "werks-enterprise"), cmc_werks)

    monkeypatch.setattr(cmk.werks, "_compiled_werks_dir", lambda: tmp_dir)
    werks_loaded = cmk.werks.load()

    merged_werks = cmk_werks
    if site.version.edition() == "raw":
        merged_werks.update(cmc_werks)

    assert merged_werks == werks_loaded
