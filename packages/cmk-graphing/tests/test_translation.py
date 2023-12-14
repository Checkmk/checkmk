#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import translation


def test_passive_check_error() -> None:
    with pytest.raises(AssertionError):
        translation.PassiveCheck("")


def test_active_check_error() -> None:
    with pytest.raises(AssertionError):
        translation.ActiveCheck("")


def test_host_check_command_error() -> None:
    with pytest.raises(AssertionError):
        translation.HostCheckCommand("")


def test_nagios_plugin_error() -> None:
    with pytest.raises(AssertionError):
        translation.NagiosPlugin("")


def test_renaming_error_empty_rename_to() -> None:
    with pytest.raises(ValueError):
        translation.Renaming("")


def test_scaling_error_scale_by_zero() -> None:
    with pytest.raises(AssertionError):
        translation.Scaling(0)


def test_renaming_and_scaling_error_empty_rename_to() -> None:
    with pytest.raises(ValueError):
        translation.RenamingAndScaling("", 1)


def test_renaming_and_scaling_error_scale_by_zero() -> None:
    with pytest.raises(AssertionError):
        translation.RenamingAndScaling("new-metric-name", 0)


def test_translation_error_empty_name() -> None:
    check_commands = [translation.PassiveCheck("passive-check")]
    translations = {"old-metric-name": translation.Renaming("new-metric-name")}
    with pytest.raises(ValueError):
        translation.Translation(name="", check_commands=check_commands, translations=translations)


def test_translation_error_missing_check_commands() -> None:
    name = "name"
    translations = {"old-metric-name": translation.Renaming("new-metric-name")}
    with pytest.raises(AssertionError):
        translation.Translation(name=name, check_commands=[], translations=translations)


def test_translation_error_missing_translations() -> None:
    name = "name"
    check_commands = [translation.PassiveCheck("check-command-name")]
    with pytest.raises(AssertionError):
        translation.Translation(name=name, check_commands=check_commands, translations={})


def test_translation_error_empty_old_name() -> None:
    name = "name"
    check_commands = [translation.PassiveCheck("check-command-name")]
    with pytest.raises(ValueError):
        translation.Translation(
            name=name,
            check_commands=check_commands,
            translations={"": translation.Renaming("new-metric-name")},
        )
