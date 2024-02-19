#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths

import cmk.ec.export as ec


def test_save_active_config(patch_omd_site: None, settings: ec.Settings) -> None:
    cmk.utils.paths.ec_main_config_file.touch()
    (cmk.utils.paths.ec_config_dir / "my-config.mk").touch()
    (cmk.utils.paths.ec_config_dir / "wato").mkdir(parents=True, exist_ok=True)
    (cmk.utils.paths.ec_config_dir / "wato/global.mk").touch()
    (cmk.utils.paths.ec_config_dir / "wato/rules.mk").touch()

    settings.paths.active_config_dir.value.mkdir(parents=True, exist_ok=True)
    (settings.paths.active_config_dir.value / "old-rules.mk").touch()

    ec.save_active_config(settings, [])

    assert sorted(cmk.utils.paths.ec_config_dir.glob("**/*.mk")) == sorted(
        [
            cmk.utils.paths.ec_config_dir / "my-config.mk",
            cmk.utils.paths.ec_config_dir / "wato/global.mk",
            cmk.utils.paths.ec_config_dir / "wato/rules.mk",
        ]
    )
    assert sorted(settings.paths.active_config_dir.value.glob("**/*.mk")) == sorted(
        [
            settings.paths.active_config_dir.value / "mkeventd.mk",
            settings.paths.active_config_dir.value / "conf.d/my-config.mk",
            settings.paths.active_config_dir.value / "conf.d/wato/global.mk",
            settings.paths.active_config_dir.value / "conf.d/wato/rules.mk",
        ]
    )


def test_save_active_config_no_active_config_dir(
    patch_omd_site: None, settings: ec.Settings
) -> None:
    cmk.utils.paths.ec_main_config_file.touch()
    (cmk.utils.paths.ec_config_dir / "my-config.mk").touch()
    (cmk.utils.paths.ec_config_dir / "wato").mkdir(parents=True, exist_ok=True)
    (cmk.utils.paths.ec_config_dir / "wato/global.mk").touch()
    (cmk.utils.paths.ec_config_dir / "wato/rules.mk").touch()

    ec.save_active_config(settings, [])

    assert sorted(cmk.utils.paths.ec_config_dir.glob("**/*.mk")) == sorted(
        [
            cmk.utils.paths.ec_config_dir / "my-config.mk",
            cmk.utils.paths.ec_config_dir / "wato/global.mk",
            cmk.utils.paths.ec_config_dir / "wato/rules.mk",
        ]
    )
    assert sorted(settings.paths.active_config_dir.value.glob("**/*.mk")) == sorted(
        [
            settings.paths.active_config_dir.value / "mkeventd.mk",
            settings.paths.active_config_dir.value / "conf.d/my-config.mk",
            settings.paths.active_config_dir.value / "conf.d/wato/global.mk",
            settings.paths.active_config_dir.value / "conf.d/wato/rules.mk",
        ]
    )
