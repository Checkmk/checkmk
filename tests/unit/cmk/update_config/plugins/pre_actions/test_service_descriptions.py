#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.update_config.plugins.pre_actions.service_descriptions import (
    action,
    find_outdated_entries,
)
from cmk.update_config.plugins.pre_actions.utils import ConflictMode

LOGGER = logging.getLogger("test")


def test_find_outdated_entries_reports_old_plugin_names(tmp_path: Path) -> None:
    main_mk = tmp_path / "main.mk"
    main_mk.write_text(
        "service_descriptions = {\n"
        '    "ps.perf": "PS %s",\n'
        '    "sap.value-groups": "SAP %s",\n'
        '    "df": "FS %s",\n'
        "}\n"
    )
    assert find_outdated_entries([main_mk]) == [
        f"{main_mk}: rename 'ps.perf' to 'ps_perf'",
        f"{main_mk}: rename 'sap.value-groups' to 'sap_value_groups'",
    ]


def test_find_outdated_entries_reports_non_string_values(tmp_path: Path) -> None:
    main_mk = tmp_path / "main.mk"
    main_mk.write_text('service_descriptions = {"df": 42}\n')
    assert find_outdated_entries([main_mk]) == [f"{main_mk}: the value for 'df' must be a string"]


def test_find_outdated_entries_reports_unanalyzable_files(tmp_path: Path) -> None:
    main_mk = tmp_path / "main.mk"
    main_mk.write_text("service_descriptions = some_undefined_helper()\n")
    issues = find_outdated_entries([main_mk])
    assert len(issues) == 1
    assert issues[0].startswith(f"{main_mk}: could not be analyzed")


def test_find_outdated_entries_skips_unrelated_files(tmp_path: Path) -> None:
    other_mk = tmp_path / "other.mk"
    other_mk.write_text("this is not even valid python\n")
    assert not find_outdated_entries([other_mk])


def test_action_passes_on_clean_config(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    main_mk = tmp_path / "main.mk"
    main_mk.write_text('service_descriptions = {"ps_perf": "PS %s"}\n')
    with caplog.at_level(logging.WARNING):
        action(LOGGER, ConflictMode.ABORT, config_file_paths=[main_mk])
    assert caplog.text == ""


def test_action_aborts_on_old_plugin_names(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    main_mk = tmp_path / "main.mk"
    main_mk.write_text('service_descriptions = {"ps.perf": "PS %s"}\n')
    with pytest.raises(MKUserError):
        action(LOGGER, ConflictMode.ABORT, config_file_paths=[main_mk])
    assert "rename 'ps.perf' to 'ps_perf'" in caplog.text


def test_action_force_continues_despite_old_plugin_names(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    main_mk = tmp_path / "main.mk"
    main_mk.write_text('service_descriptions = {"ps.perf": "PS %s"}\n')
    with caplog.at_level(logging.WARNING):
        action(LOGGER, ConflictMode.FORCE, config_file_paths=[main_mk])
    assert "rename 'ps.perf' to 'ps_perf'" in caplog.text
