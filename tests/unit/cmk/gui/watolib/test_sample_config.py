#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.utils.paths import omd_root

from cmk.gui.watolib.sample_config import init_wato_datastructures


def test_init_wato_data_structures() -> None:
    init_wato_datastructures()
    assert Path(omd_root, "etc/check_mk/conf.d/wato/rules.mk").exists()
    assert Path(omd_root, "etc/check_mk/multisite.d/wato/tags.mk").exists()
    assert Path(omd_root, "etc/check_mk/conf.d/wato/global.mk").exists()
    assert Path(omd_root, "var/check_mk/web/automation").exists()
    assert Path(omd_root, "var/check_mk/web/automation/automation.secret").exists()
