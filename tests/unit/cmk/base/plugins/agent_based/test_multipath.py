#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


@pytest.fixture(name="plugin", scope="module")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName("multipath")]


@pytest.fixture(name="discover_multipath", scope="module")
def _get_disvovery_function(plugin):
    return lambda section: plugin.discovery_function(section=section)


@pytest.fixture(name="check_multipath", scope="module")
def _get_check_function(plugin):
    return lambda item, params, section: plugin.check_function(
        item=item, params=params, section=section
    )


STRING_TABLE: Final = [
    ["ORA_ZAPPL2T_DATA_3", "(3600601604d40310047cf93ce66f7e111)", "dm-67", "DGC,RAID", "5"],
    ["size=17G", "features='1", "queue_if_no_path'", "hwhandler='1", "alua'", "wp=rw"],
    ["|-+-", "policy='round-robin", "0'", "prio=0", "status=active"],
    ["| |-", "3:0:1:54", "sddz", "128:16 ", "active", "undef", "running"],
    ["|", "`-", "5:0:1:54", "sdkb", "65:496", "active", "undef", "running"],
    ["`-+-", "policy='round-robin", "0'", "prio=0", "status=enabled"],
    ["|-", "5:0:0:54", "sdbd", "67:112", "active", "undef", "running"],
    ["`-", "3:0:0:54", "sdhf", "133:80", "active", "undef", "running"],
    ["ORA_UC41T_OLOG_1", "(3600601604d403100912ab0b365f7e111)", "dm-112", "DGC,RAID", "5"],
    ["size=17G features='1 queue_if_no_path' hwhandler='1 alua' wp=rw"],
    ["|-+-", "policy='round-robin", "0'", "prio=0", "status=active"],
    ["|", "|-", "5:0:0:77", "sdew", "129:128", "active", "undef", "running"],
]


@pytest.fixture(name="section", scope="module")
def _get_section(fix_register):
    plugin = fix_register.agent_sections[SectionName("multipath")]
    return plugin.parse_function(STRING_TABLE)


def test_discovery(monkeypatch, discover_multipath, section) -> None:
    import cmk.base.plugin_contexts
    from cmk.base.config import ConfigCache

    monkeypatch.setattr(cmk.base.plugin_contexts, "_hostname", lambda: "foo")
    monkeypatch.setattr(ConfigCache, "host_extra_conf_merged", lambda s, h, r: {})
    assert sorted(discover_multipath(section)) == [
        Service(
            item="3600601604d40310047cf93ce66f7e111", parameters={"auto-migration-wrapper-key": 4}
        ),
        Service(
            item="3600601604d403100912ab0b365f7e111", parameters={"auto-migration-wrapper-key": 1}
        ),
    ]


def test_check_percent_levels(check_multipath, section) -> None:
    assert list(
        check_multipath(
            "3600601604d40310047cf93ce66f7e111",
            # lower levels. these make no sense, but we want to see a WARN.
            {"auto-migration-wrapper-key": (110.0, 40.0)},
            section,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="(ORA_ZAPPL2T_DATA_3): Paths active: 4/4 (warn/crit below 4/1)",
        )
    ]


def test_check_count_levels(check_multipath, section) -> None:
    assert list(
        check_multipath(
            "3600601604d40310047cf93ce66f7e111",
            {"auto-migration-wrapper-key": 3},
            section,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="(ORA_ZAPPL2T_DATA_3): Paths active: 4/4, Expected paths: 3 (warn at 3)",
        )
    ]
