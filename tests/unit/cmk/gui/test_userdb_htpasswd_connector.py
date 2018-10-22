#!/usr/bin/env python
# encoding: utf-8

import pytest
import pathlib2 as pathlib

import cmk.gui.plugins.userdb.htpasswd as htpasswd

@pytest.fixture()
def htpasswd_file(tmpdir):
    htpasswd_file = tmpdir.join("htpasswd")
    htpasswd_file.write((
        u"bärnd:NEr3kqi287FQc\n"
        u"cmkadmin:NEr3kqi287FQc\n"
        u"locked:!NEr3kqi287FQc\n"
    ).encode("utf-8"), mode="wb")
    return pathlib.Path(htpasswd_file)


def test_htpasswd_exists(htpasswd_file):
    assert htpasswd.Htpasswd(htpasswd_file).exists(u"cmkadmin")
    assert htpasswd.Htpasswd(htpasswd_file).exists(u"locked")
    assert not htpasswd.Htpasswd(htpasswd_file).exists(u"not-existing")
    assert not htpasswd.Htpasswd(htpasswd_file).exists(u"")
    assert htpasswd.Htpasswd(htpasswd_file).exists(u"bärnd")


def test_htpasswd_load(htpasswd_file):
    credentials = htpasswd.Htpasswd(htpasswd_file).load()
    assert credentials[u"cmkadmin"] == "NEr3kqi287FQc"
    assert isinstance(credentials[u"cmkadmin"], unicode)
    assert credentials[u"bärnd"] == "NEr3kqi287FQc"


def test_htpasswd_save(htpasswd_file):
    credentials = htpasswd.Htpasswd(htpasswd_file).load()

    saved_file = htpasswd_file.with_suffix(".saved")
    htpasswd.Htpasswd(saved_file).save(credentials)

    assert htpasswd_file.open(encoding="utf-8").read() \
        == saved_file.open(encoding="utf-8").read()
