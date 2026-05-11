#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.ibm_mq.rulesets.bakery import migrate


def test_migrate_none() -> None:
    assert migrate(None) == {"deployment": ("do_not_deploy", None)}


def test_migrate_empty_dict() -> None:
    assert migrate({}) == {"deployment": ("sync", None)}


def test_migrate_with_only_qm() -> None:
    assert migrate({"only_qm": ["QM1", "QM2"]}) == {
        "deployment": ("sync", None),
        "only_qm": ["QM1", "QM2"],
    }


def test_migrate_with_skip_qm() -> None:
    assert migrate({"skip_qm": ["QM3"]}) == {
        "deployment": ("sync", None),
        "skip_qm": ["QM3"],
    }


def test_migrate_with_execute_as_another_user() -> None:
    assert migrate({"execute_as_another_user": "mqm"}) == {
        "deployment": ("sync", None),
        "execute_as_another_user": "mqm",
    }


def test_migrate_already_migrated_sync() -> None:
    value = {"deployment": ("sync", None), "only_qm": ["QM1"]}
    assert migrate(value) == value


def test_migrate_already_migrated_do_not_deploy() -> None:
    value = {"deployment": ("do_not_deploy", None)}
    assert migrate(value) == value


def test_migrate_invalid_raises() -> None:
    with pytest.raises(ValueError):
        migrate("unexpected_string")
