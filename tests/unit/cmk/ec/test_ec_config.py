#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths

import cmk.ec.export as ec
from cmk.ec.settings import create_paths


def test_save_active_config(patch_omd_site: None) -> None:
    cmk.utils.paths.ec_main_config_file.touch()
    (cmk.utils.paths.ec_config_dir / "my-config.mk").touch()
    (cmk.utils.paths.ec_config_dir / "wato").mkdir(parents=True, exist_ok=True)
    (cmk.utils.paths.ec_config_dir / "wato/global.mk").touch()
    (cmk.utils.paths.ec_config_dir / "wato/rules.mk").touch()

    active_config_dir = create_paths(cmk.utils.paths.omd_root).active_config_dir.value
    active_config_dir.mkdir(parents=True, exist_ok=True)
    (active_config_dir / "old-rules.mk").touch()

    ec.save_active_config([])

    assert sorted(cmk.utils.paths.ec_config_dir.glob("**/*.mk")) == sorted(
        [
            cmk.utils.paths.ec_config_dir / "my-config.mk",
            cmk.utils.paths.ec_config_dir / "wato/global.mk",
            cmk.utils.paths.ec_config_dir / "wato/rules.mk",
        ]
    )
    assert sorted(active_config_dir.glob("**/*.mk")) == sorted(
        [
            active_config_dir / "mkeventd.mk",
            active_config_dir / "conf.d/my-config.mk",
            active_config_dir / "conf.d/wato/global.mk",
            active_config_dir / "conf.d/wato/rules.mk",
        ]
    )


def test_save_active_config_no_active_config_dir(patch_omd_site: None) -> None:
    cmk.utils.paths.ec_main_config_file.touch()
    (cmk.utils.paths.ec_config_dir / "my-config.mk").touch()
    (cmk.utils.paths.ec_config_dir / "wato").mkdir(parents=True, exist_ok=True)
    (cmk.utils.paths.ec_config_dir / "wato/global.mk").touch()
    (cmk.utils.paths.ec_config_dir / "wato/rules.mk").touch()

    ec.save_active_config([])

    assert sorted(cmk.utils.paths.ec_config_dir.glob("**/*.mk")) == sorted(
        [
            cmk.utils.paths.ec_config_dir / "my-config.mk",
            cmk.utils.paths.ec_config_dir / "wato/global.mk",
            cmk.utils.paths.ec_config_dir / "wato/rules.mk",
        ]
    )
    active_config_dir = create_paths(cmk.utils.paths.omd_root).active_config_dir.value
    assert sorted(active_config_dir.glob("**/*.mk")) == sorted(
        [
            active_config_dir / "mkeventd.mk",
            active_config_dir / "conf.d/my-config.mk",
            active_config_dir / "conf.d/wato/global.mk",
            active_config_dir / "conf.d/wato/rules.mk",
        ]
    )
