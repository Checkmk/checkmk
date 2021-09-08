#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import omdlib.main


@pytest.fixture()
def site_context(tmp_path, monkeypatch):
    monkeypatch.setattr(
        omdlib.main.SiteContext, "dir", property(lambda s: "%s/omd/sites/%s" % (tmp_path, s.name))
    )
    monkeypatch.setattr(
        omdlib.main.SiteContext,
        "real_dir",
        property(lambda s: "%s/opt/omd/sites/%s" % (tmp_path, s.name)),
    )

    return omdlib.main.SiteContext("unit")
