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


def test_renaming_error() -> None:
    with pytest.raises(AssertionError):
        translation.Renaming("")


def test_scaling_error() -> None:
    with pytest.raises(AssertionError):
        translation.Scaling(0)


def test_renaming_and_scaling_error_rename_to_empty() -> None:
    with pytest.raises(AssertionError):
        translation.RenamingAndScaling(rename_to="", scale_by=1)


def test_renaming_and_scaling_error_scale_by_zero() -> None:
    with pytest.raises(AssertionError):
        translation.RenamingAndScaling(rename_to="new-name", scale_by=0)


def test_translations_error_missing_name() -> None:
    check_commands = [translation.PassiveCheck("check-command-name")]
    translations = {"old-name": translation.Renaming("new-name")}
    with pytest.raises(AssertionError):
        translation.Translations(
            name="",
            check_commands=check_commands,
            translations=translations,
        )


def test_translations_error_missing_check_commands() -> None:
    translations = {"old-name": translation.Renaming("new-name")}
    with pytest.raises(AssertionError):
        translation.Translations(
            name="name",
            check_commands=[],
            translations=translations,
        )


def test_translations_error_missing_translations() -> None:
    check_commands = [translation.PassiveCheck("check-command-name")]
    with pytest.raises(AssertionError):
        translation.Translations(
            name="name",
            check_commands=check_commands,
            translations={},
        )
