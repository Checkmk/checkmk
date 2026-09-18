#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.icon_helpers import migrate_to_dynamic_icon, migrate_to_static_icon
from cmk.shared_typing.main_menu import DefaultIcon, EmblemIcon
from cmk.web.utils.icons import DynamicIconName, IconNames, StaticIcon


@pytest.mark.parametrize(
    "icon_name, expected_id",
    [
        pytest.param("about_checkmk", "about-checkmk", id="underscore-form"),
        pytest.param("about-checkmk", "about-checkmk", id="hyphen-form"),
        pytest.param("2fa", "2fa", id="legacy-icon-added-to-enum"),
        pytest.param("2fa_backup_codes", "2fa-backup-codes", id="legacy-icon-underscore"),
        pytest.param("cache", "missing", id="renamed-legacy-icon-falls-back"),
        pytest.param("does_not_exist_xyz", "missing", id="unknown-icon-falls-back"),
    ],
)
def test_migrate_to_dynamic_icon_from_string(icon_name: str, expected_id: str) -> None:
    assert migrate_to_dynamic_icon(icon_name) == DefaultIcon(id=IconNames(expected_id))


def test_migrate_to_dynamic_icon_none_returns_none() -> None:
    assert migrate_to_dynamic_icon(None) is None


def test_migrate_to_dynamic_icon_from_dict_with_emblem() -> None:
    resolved = migrate_to_dynamic_icon({"icon": DynamicIconName("cache"), "emblem": "warning"})

    assert resolved == EmblemIcon(icon=DefaultIcon(id=IconNames.missing), emblem="warning")


def test_migrate_to_static_icon_unknown_falls_back_to_missing() -> None:
    resolved = migrate_to_static_icon(DefaultIcon(id="cache"))

    assert resolved == StaticIcon(IconNames.missing)


def test_migrate_to_static_icon_with_emblem() -> None:
    resolved = migrate_to_static_icon(
        EmblemIcon(icon=DefaultIcon(id="cache"), emblem="warning"),
    )

    assert resolved == StaticIcon(IconNames.missing, emblem="warning")
