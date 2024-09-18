#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Service
from cmk.plugins.collection.agent_based import df_zos
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

STRING_TABLE = [
    line.split()
    for line in """
SYS5.OMVS.ALF0.HFS         720          92        504       16% /ALF0
HFS, Read/Write, Device:2, ACLS=Y
Filetag : T=off   codeset=0
##########
SYS5.OMVS.SYSPLEX.ROOT     720         224        372       38% /
HFS, Read Only, Device:1, ACLS=Y
Filetag : T=off   codeset=0
##########
""".strip().split("\n")
]


@pytest.fixture(scope="module", name="section")
def _get_section() -> df_zos.Section:
    return df_zos.parse_df_zos(STRING_TABLE)


def test_discovery(section: df_zos.Section) -> None:
    assert sorted(df_zos.discover_df_zos([{"groups": []}], section)) == [Service(item="/ALF0")]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_no_item(section: df_zos.Section) -> None:
    assert not list(df_zos.check_df_zos("knut", {}, section))


def test_check_grouped(section: df_zos.Section, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(df_zos, "get_value_store", lambda: {"knut.delta": (0, 9435.0)})
    assert list(
        df_zos.check_df_zos("knut", {**FILESYSTEM_DEFAULT_PARAMS, "patterns": (["*"], [])}, section)
    )


def test_check_single_item(section: df_zos.Section, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(df_zos, "get_value_store", lambda: {"/ALF0.delta": (0, 424242)})
    assert list(df_zos.check_df_zos("/ALF0", FILESYSTEM_DEFAULT_PARAMS, section))
