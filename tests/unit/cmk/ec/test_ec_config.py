#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.utils.paths

import cmk.ec.export as ec
from cmk.ec.rule_packs import load_active_config
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


@pytest.fixture(name="isolated_ec_config")
def fixture_isolated_ec_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Starts without any configuration files of other tests, e.g. rule packs"""
    monkeypatch.setattr(cmk.utils.paths, "ec_main_config_file", tmp_path / "mkeventd.mk")
    monkeypatch.setattr(cmk.utils.paths, "ec_config_dir", tmp_path / "mkeventd.d")


@pytest.mark.usefixtures("isolated_ec_config")
def test_config_to_activate_is_the_one_the_ec_loads_after_activating_it(
    settings: ec.Settings,
) -> None:
    (cmk.utils.paths.ec_config_dir / "wato").mkdir(parents=True)
    (cmk.utils.paths.ec_config_dir / "wato/global.mk").write_text(
        'hostname_translation = {"case": "lower"}\n'
    )
    cmk.utils.paths.ec_main_config_file.write_text('hostname_translation = {"case": "upper"}\n')
    config_to_activate = ec.load_config_to_activate(ec.mkp_rule_pack_dir())

    ec.save_active_config([])

    assert load_active_config(settings) == config_to_activate


@pytest.mark.usefixtures("isolated_ec_config")
def test_config_to_activate_does_not_load_the_rule_packs() -> None:
    # Loading any of these rule packs would fail.
    mkp_rule_pack_dir = cmk.utils.paths.ec_config_dir / "mkp/rule_packs"
    mkp_rule_pack_dir.mkdir(parents=True)
    (mkp_rule_pack_dir / "packaged.mk").write_text("this is no rule pack (\n")
    (cmk.utils.paths.ec_config_dir / "wato").mkdir(parents=True)
    (cmk.utils.paths.ec_config_dir / "wato/rules.mk").write_text("this is no rule pack (\n")
    cmk.utils.paths.ec_main_config_file.write_text('hostname_translation = {"case": "upper"}\n')

    config_to_activate = ec.load_config_to_activate(mkp_rule_pack_dir)

    assert config_to_activate["hostname_translation"] == {"case": "upper"}


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
