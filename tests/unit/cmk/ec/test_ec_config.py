#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ec.export import save_active_config
from cmk.ec.settings import Settings


def test_save_active_config(settings: Settings) -> None:
    (settings.paths.config_dir.value / "my-config.mk").touch()
    (settings.paths.config_dir.value / "wato").mkdir(parents=True, exist_ok=True)
    (settings.paths.config_dir.value / "wato/global.mk").touch()
    (settings.paths.config_dir.value / "wato/rules.mk").touch()
    save_active_config(settings, [])
    assert sorted(settings.paths.config_dir.value.glob("**/*.mk")) == (
        [
            settings.paths.config_dir.value / "my-config.mk",
            settings.paths.config_dir.value / "wato/global.mk",
            settings.paths.config_dir.value / "wato/rules.mk",
        ]
    )
    assert sorted(settings.paths.active_config_dir.value.glob("**/*.mk")) == (
        [
            settings.paths.active_config_dir.value / "my-config.mk",
            settings.paths.active_config_dir.value / "wato/global.mk",
            settings.paths.active_config_dir.value / "wato/rules.mk",
        ]
    )
