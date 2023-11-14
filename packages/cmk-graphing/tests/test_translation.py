#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import translation


def test_name_error() -> None:
    with pytest.raises(ValueError):
        translation.Name("")


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


def test_scaling_error() -> None:
    with pytest.raises(AssertionError):
        translation.Scaling(0)


def test_renaming_and_scaling_error_scale_by_zero() -> None:
    with pytest.raises(AssertionError):
        translation.RenamingAndScaling(translation.Name("new-name"), 0)


def test_translations_error_missing_check_commands() -> None:
    name = translation.Name("name")
    translations = {
        translation.Name("old-name"): translation.Renaming(translation.Name("new-name"))
    }
    with pytest.raises(AssertionError):
        translation.Translations(name, [], translations)


def test_translations_error_missing_translations() -> None:
    name = translation.Name("name")
    check_commands = [translation.PassiveCheck("check-command-name")]
    with pytest.raises(AssertionError):
        translation.Translations(name, check_commands, {})
