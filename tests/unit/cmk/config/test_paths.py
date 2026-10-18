#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.config.paths import BaseConfigurationMKFiles


def test_base_configuration_mk_files_from_omd_root() -> None:
    assert BaseConfigurationMKFiles.from_omd_root(
        Path("/omd/sites/heute")
    ) == BaseConfigurationMKFiles(
        main_mk=Path("/omd/sites/heute/etc/check_mk/main.mk"),
        conf_d=Path("/omd/sites/heute/etc/check_mk/conf.d"),
        final_mk=Path("/omd/sites/heute/etc/check_mk/final.mk"),
        local_mk=Path("/omd/sites/heute/etc/check_mk/local.mk"),
    )
