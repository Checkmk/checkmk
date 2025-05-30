#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os

import pytest

from omdlib.contexts import SiteContext


def test_site_context() -> None:
    site = SiteContext("dingeling")
    assert site.name == "dingeling"
    assert site.real_dir == "/opt/omd/sites/dingeling"
    assert site.tmp_dir == "/omd/sites/dingeling/tmp"
    assert site.version_meta_dir == "/omd/sites/dingeling/.version_meta"


def test_site_context_replacements(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "readlink", lambda x: "../2018.08.11.cee")
    site = SiteContext("dingeling")
    replacements = site.replacements()

    assert replacements["###SITE###"] == "dingeling"
    assert replacements["###ROOT###"] == "/omd/sites/dingeling"
    assert replacements["###EDITION###"] in ("raw", "enterprise", "cloud", "managed")
    assert len(replacements) == 3


def test_site_context_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        os, "listdir", lambda p: [] if p == "/omd/sites/dingeling" else ["abc", "version"]
    )

    site = SiteContext("dingeling")
    assert site.is_empty()

    site = SiteContext("dingelang")
    assert not site.is_empty()
