#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.flags import CONFIG_FILENAME, load_experimental_flags
from cmk.gui.experimental_flags import global_config
from cmk.gui.experimental_flags.global_config import (
    ConfigDomainExperimentalFlags,
    EXPERIMENTAL_FLAGS_STAGED_FILENAME,
)


@pytest.fixture(name="config_dir")
def fixture_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(global_config, "EXPERIMENTAL_FLAGS_CONFIG_DIR", tmp_path)
    return tmp_path


def test_saving_a_flag_does_not_change_the_active_flags(config_dir: Path) -> None:
    ConfigDomainExperimentalFlags().save({"exp_ai_assistant": True})

    assert not load_experimental_flags(config_dir).exp_ai_assistant


def test_saved_flags_are_applied_before_any_domain_activates(config_dir: Path) -> None:
    domain = ConfigDomainExperimentalFlags()
    domain.save({"exp_ai_assistant": True})

    domain.create_artifacts()

    assert load_experimental_flags(config_dir).exp_ai_assistant


def test_activation_removes_the_saved_flags(config_dir: Path) -> None:
    domain = ConfigDomainExperimentalFlags()
    domain.save({"exp_ai_assistant": True})

    domain.create_artifacts()

    assert not (config_dir / EXPERIMENTAL_FLAGS_STAGED_FILENAME).exists()


def test_activating_without_saved_flags_keeps_the_active_flags(config_dir: Path) -> None:
    (config_dir / CONFIG_FILENAME).write_text('{"exp_ai_assistant": true}')

    ConfigDomainExperimentalFlags().create_artifacts()

    assert load_experimental_flags(config_dir).exp_ai_assistant


def test_settings_show_the_saved_flags_before_activation(config_dir: Path) -> None:
    (config_dir / CONFIG_FILENAME).write_text('{"exp_ai_assistant": false}')
    domain = ConfigDomainExperimentalFlags()
    domain.save({"exp_ai_assistant": True})

    assert domain.load_full_config() == {"exp_ai_assistant": True}


def test_settings_show_the_active_flags_when_nothing_is_saved(config_dir: Path) -> None:
    (config_dir / CONFIG_FILENAME).write_text('{"exp_ai_assistant": true}')

    assert ConfigDomainExperimentalFlags().load_full_config() == {"exp_ai_assistant": True}
