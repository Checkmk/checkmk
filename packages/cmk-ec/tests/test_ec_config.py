#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import cmk.ec.export as ec
from cmk.ec.rule_packs import load_active_config


def test_save_active_config(tmp_path: Path) -> None:
    paths = ec.create_paths(tmp_path)
    ec_config_dir = paths.config_dir.value
    ec_config_dir.mkdir(parents=True)
    paths.main_config_file.value.touch()
    (ec_config_dir / "my-config.mk").touch()
    (ec_config_dir / "wato").mkdir(parents=True, exist_ok=True)
    (ec_config_dir / "wato/global.mk").touch()
    (ec_config_dir / "wato/rules.mk").touch()

    active_config_dir = ec.create_paths(tmp_path).active_config_dir.value
    active_config_dir.mkdir(parents=True, exist_ok=True)
    (active_config_dir / "old-rules.mk").touch()

    ec.save_active_config([], tmp_path)

    assert sorted(ec_config_dir.glob("**/*.mk")) == sorted(
        [
            ec_config_dir / "my-config.mk",
            ec_config_dir / "wato/global.mk",
            ec_config_dir / "wato/rules.mk",
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


def test_config_to_activate_is_the_one_the_ec_loads_after_activating_it(
    tmp_path: Path, settings: ec.Settings
) -> None:
    paths = ec.create_paths(tmp_path)
    (paths.config_dir.value / "wato").mkdir(parents=True)
    (paths.config_dir.value / "wato/global.mk").write_text(
        'hostname_translation = {"case": "lower"}\n'
    )
    paths.main_config_file.value.write_text('hostname_translation = {"case": "upper"}\n')
    config_to_activate = ec.load_config_to_activate(paths)

    ec.save_active_config([], tmp_path)

    assert load_active_config(settings) == config_to_activate


def test_save_active_config_no_active_config_dir(tmp_path: Path) -> None:
    paths = ec.create_paths(tmp_path)
    ec_config_dir = paths.config_dir.value
    ec_config_dir.mkdir(parents=True)
    paths.main_config_file.value.touch()
    (ec_config_dir / "my-config.mk").touch()
    (ec_config_dir / "wato").mkdir(parents=True, exist_ok=True)
    (ec_config_dir / "wato/global.mk").touch()
    (ec_config_dir / "wato/rules.mk").touch()

    ec.save_active_config([], tmp_path)

    assert sorted(ec_config_dir.glob("**/*.mk")) == sorted(
        [
            ec_config_dir / "my-config.mk",
            ec_config_dir / "wato/global.mk",
            ec_config_dir / "wato/rules.mk",
        ]
    )
    active_config_dir = ec.create_paths(tmp_path).active_config_dir.value
    assert sorted(active_config_dir.glob("**/*.mk")) == sorted(
        [
            active_config_dir / "mkeventd.mk",
            active_config_dir / "conf.d/my-config.mk",
            active_config_dir / "conf.d/wato/global.mk",
            active_config_dir / "conf.d/wato/rules.mk",
        ]
    )
