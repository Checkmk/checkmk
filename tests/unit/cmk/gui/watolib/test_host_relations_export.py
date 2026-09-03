#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for the monitoring-core export of host relations."""

import json
import logging
from collections.abc import Mapping
from pathlib import Path

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.hostaddress import HostName
from cmk.gui.utils.host_relations import RELATIONS_MACRO
from cmk.gui.watolib.activate_changes import ActivateChangesManager
from cmk.gui.watolib.host_relations import RelatedHost
from cmk.gui.watolib.host_relations_export import export_host_relations, relations_export_path
from tests.unit.cmk.gui.watolib.host_relations_fakes import fake_hosts


def _exported_macro(export_file: Path) -> dict[str, str]:
    """The ``_RELATIONS`` variable the way the core reads the generated file back."""
    namespace: dict[str, dict[str, dict[str, str]]] = {"explicit_host_conf": {}}
    exec(export_file.read_text(), namespace)  # this is exactly how the core loads it
    return namespace["explicit_host_conf"][RELATIONS_MACRO]


def test_export_writes_both_sides_of_a_relation(tmp_path: Path) -> None:
    export_file = tmp_path / "relations.mk"

    export_host_relations(
        fake_hosts(srv=[{"kind": "management", "direction": "child", "host": "mgmt"}], mgmt=None),
        export_file,
    )

    macro = _exported_macro(export_file)
    assert json.loads(macro["srv"]) == [
        {"kind": "management", "direction": "child", "host": "mgmt", "site": "central"}
    ]
    assert json.loads(macro["mgmt"]) == [
        {"kind": "management", "direction": "parent", "host": "srv", "site": "central"}
    ]


def test_export_declares_the_macro_even_without_relations(tmp_path: Path) -> None:
    """The file always states the variable, so removing the last relation clears the core's."""
    export_file = tmp_path / "relations.mk"

    export_host_relations(fake_hosts(plain=None), export_file)

    assert f"explicit_host_conf.setdefault({RELATIONS_MACRO!r}, {{}})" in export_file.read_text()
    assert _exported_macro(export_file) == {}


def test_export_leaves_an_unchanged_file_untouched(tmp_path: Path) -> None:
    """A config file in conf.d that is newer than the last core compilation costs the CMC its
    incremental activation, and this export runs on every activation."""
    export_file = tmp_path / "relations.mk"
    hosts = fake_hosts(
        srv=[{"kind": "management", "direction": "child", "host": "mgmt"}], mgmt=None
    )
    export_host_relations(hosts, export_file)
    mtime = export_file.stat().st_mtime_ns

    export_host_relations(hosts, export_file)

    assert export_file.stat().st_mtime_ns == mtime


def test_export_rewrites_a_file_whose_relations_changed(tmp_path: Path) -> None:
    export_file = tmp_path / "relations.mk"
    export_host_relations(
        fake_hosts(srv=[{"kind": "management", "direction": "child", "host": "mgmt"}], mgmt=None),
        export_file,
    )

    export_host_relations(fake_hosts(srv=None, mgmt=None), export_file)

    assert _exported_macro(export_file) == {}


@pytest.mark.parametrize(
    "all_hosts, hosts, entries",
    [
        pytest.param(
            fake_hosts(
                srv=[{"kind": "management", "direction": "child", "host": "mgmt"}], mgmt=None
            ),
            2,
            2,
            id="one relation, counted on both of its hosts",
        ),
        pytest.param(fake_hosts(plain=None), 0, 0, id="nothing configured"),
    ],
)
def test_activation_summary_is_logged(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    all_hosts: Mapping[HostName, RelatedHost],
    hosts: int,
    entries: int,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="cmk.web.host_relations"):
        export_host_relations(all_hosts, tmp_path / "relations.mk")

    summary = caplog.records[-1].args
    assert isinstance(summary, Mapping)
    assert summary["hosts"] == hosts
    assert summary["entries"] == entries
    assert str(summary["path"]).endswith("relations.mk")


@pytest.mark.usefixtures("with_admin_login", "load_config")
def test_activation_exports_the_relations() -> None:
    """Pins the wiring: the activation itself writes the export file, where config sync finds it."""
    ActivateChangesManager()._pre_activate_changes(  # noqa: SLF001
        SiteConfigurations({}), debug=True
    )

    assert RELATIONS_MACRO in relations_export_path().read_text()
