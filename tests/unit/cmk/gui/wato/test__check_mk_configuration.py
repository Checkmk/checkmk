#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import patch

from cmk.gui.wato._check_mk_configuration import migrate_snmp_fetch_interval


def test_migrate_snmp_fetch_interval_single() -> None:
    assert migrate_snmp_fetch_interval(("foo.bar", 42)) == (["foo"], ("cached", 42.0 * 60.0))
    assert migrate_snmp_fetch_interval(migrate_snmp_fetch_interval(("foo.bar", 42))) == (
        ["foo"],
        ("cached", 42.0 * 60.0),
    )


def test_migrate_snmp_fetch_interval_all() -> None:
    with patch(
        "cmk.gui.wato._check_mk_configuration.get_snmp_section_names",
        return_value=[("foo", "foo"), ("bar", "bar")],
    ):
        assert migrate_snmp_fetch_interval((None, 3)) == (["foo", "bar"], ("cached", 3.0 * 60.0))
        assert migrate_snmp_fetch_interval(migrate_snmp_fetch_interval((None, 3))) == (
            ["foo", "bar"],
            ("cached", 3.0 * 60.0),
        )


def test_migrate_snmp_fetch_interval_already_migrated_single_cached() -> None:
    new = (["foo"], ("cached", 42.0 * 60.0))
    assert migrate_snmp_fetch_interval(new) == new


def test_migrate_snmp_fetch_interval_already_migrated_single_uncached() -> None:
    new = (["foo"], ("uncached", None))
    assert migrate_snmp_fetch_interval(new) == new


def test_migrate_snmp_fetch_interval_all_already_migrate_cached() -> None:
    new = (["foo", "bar"], ("cached", 3.0 * 60.0))
    with patch(
        "cmk.gui.wato._check_mk_configuration.get_snmp_section_names",
        return_value=[("foo", "foo"), ("bar", "bar")],
    ):
        assert migrate_snmp_fetch_interval(new) == new


def test_migrate_snmp_fetch_interval_all_already_migrate_uncached() -> None:
    new = (["foo", "bar"], ("uncached", None))
    with patch(
        "cmk.gui.wato._check_mk_configuration.get_snmp_section_names",
        return_value=[("foo", "foo"), ("bar", "bar")],
    ):
        assert migrate_snmp_fetch_interval(new) == new
