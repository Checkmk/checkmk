#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import cmk.utils.version as cmk_version
import cmk.utils.paths


# Would move this to unit tests, but it would not work, because the
# unit tests monkeypatch the cmk_version.omd_version() function
def test_omd_version(tmp_path, monkeypatch):
    link_path = str(tmp_path / "version")

    monkeypatch.setattr(cmk.utils.paths, 'omd_root', os.path.dirname(link_path))

    os.symlink("/omd/versions/2016.09.12.cee", link_path)
    cmk_version.omd_version.cache_clear()
    assert cmk_version.omd_version() == "2016.09.12.cee"
    os.unlink(link_path)

    os.symlink("/omd/versions/2016.09.12.cee.demo", link_path)
    cmk_version.omd_version.cache_clear()
    assert cmk_version.omd_version() == "2016.09.12.cee.demo"
    os.unlink(link_path)
