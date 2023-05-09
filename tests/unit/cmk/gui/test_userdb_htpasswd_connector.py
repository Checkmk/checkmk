#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest  # type: ignore[import]
from passlib.hash import sha256_crypt  # type: ignore[import]

import cmk.gui.plugins.userdb.htpasswd as htpasswd


@pytest.fixture(name="htpasswd_file")
def htpasswd_file_fixture(tmp_path):
    htpasswd_file_path = tmp_path / "htpasswd"
    htpasswd_file_path.write_text(
        (
            # Pre 1.6 hashing formats (see cmk.gui.plugins.userdb.htpasswd for more details)
            u"bärnd:$apr1$/FU.SwEZ$Ye0XG1Huf2j7Jws7KD.h2/\n"
            u"cmkadmin:NEr3kqi287FQc\n"
            u"harry:$1$478020$ldQUQ3RIwRYk5wjKfsWPD.\n"
            # A disabled user
            u"locked:!NEr3kqi287FQc\n"
            # A >= 1.6 sha256 hashed password
            u"sha256user:$5$rounds=535000$5IFtH0zYpQ6STBre$Nkem2taHfBFswWj3xERRpmEI.20G5is0VBcPpUuf3J2\n"
        ),
        encoding="utf-8")
    return Path(htpasswd_file_path)


def test_htpasswd_exists(htpasswd_file):
    assert htpasswd.Htpasswd(htpasswd_file).exists(u"cmkadmin")
    assert htpasswd.Htpasswd(htpasswd_file).exists(u"locked")
    assert not htpasswd.Htpasswd(htpasswd_file).exists(u"not-existing")
    assert not htpasswd.Htpasswd(htpasswd_file).exists(u"")
    assert htpasswd.Htpasswd(htpasswd_file).exists(u"bärnd")


def test_htpasswd_load(htpasswd_file):
    credentials = htpasswd.Htpasswd(htpasswd_file).load()
    assert credentials[u"cmkadmin"] == "NEr3kqi287FQc"
    assert isinstance(credentials[u"cmkadmin"], str)
    assert credentials[u"bärnd"] == "$apr1$/FU.SwEZ$Ye0XG1Huf2j7Jws7KD.h2/"


def test_htpasswd_save(htpasswd_file):
    credentials = htpasswd.Htpasswd(htpasswd_file).load()

    saved_file = htpasswd_file.with_suffix(".saved")
    htpasswd.Htpasswd(saved_file).save(credentials)

    assert htpasswd_file.open(encoding="utf-8").read() \
        == saved_file.open(encoding="utf-8").read()


def test_hash_password():
    hashed_pw = htpasswd.hash_password("blä")
    assert sha256_crypt.verify(u"blä", hashed_pw)

    hashed_pw = htpasswd.hash_password(u"blä")
    assert sha256_crypt.verify("blä", hashed_pw)


def test_user_connector_verify_password(htpasswd_file, monkeypatch):
    c = htpasswd.HtpasswdUserConnector({})
    monkeypatch.setattr(c, "_get_htpasswd", lambda: htpasswd.Htpasswd(htpasswd_file))

    assert c.check_credentials(u"cmkadmin", u"cmk") == u"cmkadmin"
    assert c.check_credentials(u"bärnd", u"cmk") == u"bärnd"
    assert c.check_credentials(u"sha256user", u"cmk") == u"sha256user"
    assert c.check_credentials(u"harry", u"cmk") == u"harry"
    assert c.check_credentials(u"dingeling", u"aaa") is None
    assert c.check_credentials(u"locked", u"locked") is False
