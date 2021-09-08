#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from passlib.hash import sha256_crypt  # type: ignore[import]

import cmk.gui.plugins.userdb.htpasswd as htpasswd


@pytest.fixture(name="htpasswd_file")
def htpasswd_file_fixture(tmp_path):
    htpasswd_file_path = tmp_path / "htpasswd"
    htpasswd_file_path.write_text(
        (
            # Pre 1.6 hashing formats (see cmk.gui.plugins.userdb.htpasswd for more details)
            "bärnd:$apr1$/FU.SwEZ$Ye0XG1Huf2j7Jws7KD.h2/\n"
            "cmkadmin:NEr3kqi287FQc\n"
            "harry:$1$478020$ldQUQ3RIwRYk5wjKfsWPD.\n"
            # A disabled user
            "locked:!NEr3kqi287FQc\n"
            # A >= 1.6 sha256 hashed password
            "sha256user:$5$rounds=535000$5IFtH0zYpQ6STBre$Nkem2taHfBFswWj3xERRpmEI.20G5is0VBcPpUuf3J2\n"
        ),
        encoding="utf-8",
    )
    return Path(htpasswd_file_path)


def test_htpasswd_exists(htpasswd_file):
    assert htpasswd.Htpasswd(htpasswd_file).exists("cmkadmin")
    assert htpasswd.Htpasswd(htpasswd_file).exists("locked")
    assert not htpasswd.Htpasswd(htpasswd_file).exists("not-existing")
    assert not htpasswd.Htpasswd(htpasswd_file).exists("")
    assert htpasswd.Htpasswd(htpasswd_file).exists("bärnd")


def test_htpasswd_load(htpasswd_file):
    credentials = htpasswd.Htpasswd(htpasswd_file).load()
    assert credentials["cmkadmin"] == "NEr3kqi287FQc"
    assert isinstance(credentials["cmkadmin"], str)
    assert credentials["bärnd"] == "$apr1$/FU.SwEZ$Ye0XG1Huf2j7Jws7KD.h2/"


def test_htpasswd_save(htpasswd_file):
    credentials = htpasswd.Htpasswd(htpasswd_file).load()

    saved_file = htpasswd_file.with_suffix(".saved")
    htpasswd.Htpasswd(saved_file).save(credentials)

    assert htpasswd_file.open(encoding="utf-8").read() == saved_file.open(encoding="utf-8").read()


def test_hash_password():
    hashed_pw = htpasswd.hash_password("blä")
    assert sha256_crypt.verify("blä", hashed_pw)

    hashed_pw = htpasswd.hash_password("blä")
    assert sha256_crypt.verify("blä", hashed_pw)


def test_user_connector_verify_password(htpasswd_file, monkeypatch):
    c = htpasswd.HtpasswdUserConnector({})
    monkeypatch.setattr(c, "_get_htpasswd", lambda: htpasswd.Htpasswd(htpasswd_file))

    assert c.check_credentials("cmkadmin", "cmk") == "cmkadmin"
    assert c.check_credentials("bärnd", "cmk") == "bärnd"
    assert c.check_credentials("sha256user", "cmk") == "sha256user"
    assert c.check_credentials("harry", "cmk") == "harry"
    assert c.check_credentials("dingeling", "aaa") is None
    assert c.check_credentials("locked", "locked") is False
