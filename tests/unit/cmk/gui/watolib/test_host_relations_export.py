#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for the monitoring-core export of host relations."""

import json
import logging
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.config import Config
from cmk.gui.utils.host_relations import RELATIONS_MACRO, ResolvedRelation
from cmk.gui.watolib import activate_changes
from cmk.gui.watolib.activate_changes import ActivateChangesManager, SiteActivationState
from cmk.gui.watolib.host_relations import RelatedHost
from cmk.gui.watolib.host_relations_export import (
    add_dropped_relations,
    dropped_relations_of_site,
    DROPPED_RELATIONS_WARNING_KEY,
    export_host_relations,
    read_dropped_relations,
    read_host_relations,
    relations_dropped_path,
    relations_export_path,
    write_dropped_relations,
)
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.utils.automation_config import RemoteAutomationConfig
from tests.unit.cmk.gui.watolib.host_relations_fakes import fake_hosts, FakeHost


def _exported_macro(export_file: Path) -> dict[str, str]:
    """The ``_CMK_RELATIONS`` variable the way the core reads the generated file back."""
    namespace: dict[str, dict[str, dict[str, str]]] = {"explicit_host_conf": {}}
    exec(export_file.read_text(), namespace)  # this is exactly how the core loads it
    return namespace["explicit_host_conf"][RELATIONS_MACRO]


def test_export_writes_both_sides_of_a_relation(tmp_path: Path) -> None:
    export_file = tmp_path / "relations.mk"

    export_host_relations(
        fake_hosts(mgmt=[{"kind": "management", "direction": "parent", "host": "srv"}], srv=None),
        export_file,
        tmp_path / "dropped.mk",
    )

    macro = _exported_macro(export_file)
    assert json.loads(macro["srv"]) == [
        {"kind": "management", "direction": "child", "host": "mgmt", "site": "central"}
    ]
    assert json.loads(macro["mgmt"]) == [
        {"kind": "management", "direction": "parent", "host": "srv", "site": "central"}
    ]


def test_export_reads_back_as_it_was_resolved(tmp_path: Path) -> None:
    export_file = tmp_path / "relations.mk"
    export_host_relations(
        fake_hosts(mgmt=[{"kind": "management", "direction": "parent", "host": "srv"}], srv=None),
        export_file,
        tmp_path / "dropped.mk",
    )

    assert read_host_relations(export_file) == {
        HostName("srv"): [
            ResolvedRelation(kind="management", direction="child", host="mgmt", site="central")
        ],
        HostName("mgmt"): [
            ResolvedRelation(kind="management", direction="parent", host="srv", site="central")
        ],
    }


def test_a_missing_export_reads_as_no_relations(tmp_path: Path) -> None:
    assert read_host_relations(tmp_path / "relations.mk") == {}


def test_export_declares_the_macro_even_without_relations(tmp_path: Path) -> None:
    """The file always states the variable, so removing the last relation clears the core's."""
    export_file = tmp_path / "relations.mk"

    export_host_relations(fake_hosts(plain=None), export_file, tmp_path / "dropped.mk")

    assert f"explicit_host_conf.setdefault({RELATIONS_MACRO!r}, {{}})" in export_file.read_text()
    assert _exported_macro(export_file) == {}


def test_export_leaves_an_unchanged_file_untouched(tmp_path: Path) -> None:
    """A config file in conf.d that is newer than the last core compilation costs the CMC its
    incremental activation, and this export runs on every activation."""
    export_file = tmp_path / "relations.mk"
    hosts = fake_hosts(
        mgmt=[{"kind": "management", "direction": "parent", "host": "srv"}], srv=None
    )
    export_host_relations(hosts, export_file, tmp_path / "dropped.mk")
    mtime = export_file.stat().st_mtime_ns

    export_host_relations(hosts, export_file, tmp_path / "dropped.mk")

    assert export_file.stat().st_mtime_ns == mtime


def test_export_rewrites_a_file_whose_relations_changed(tmp_path: Path) -> None:
    export_file = tmp_path / "relations.mk"
    export_host_relations(
        fake_hosts(mgmt=[{"kind": "management", "direction": "parent", "host": "srv"}], srv=None),
        export_file,
        tmp_path / "dropped.mk",
    )

    export_host_relations(fake_hosts(srv=None, mgmt=None), export_file, tmp_path / "dropped.mk")

    assert _exported_macro(export_file) == {}


def _contradicting_hosts() -> Mapping[HostName, RelatedHost]:
    return fake_hosts(
        board=[{"kind": "management", "direction": "parent", "host": "os1"}],
        os1=[{"kind": "management", "direction": "parent", "host": "board"}],
    )


def test_export_writes_what_it_dropped(tmp_path: Path) -> None:
    dropped_file = tmp_path / "dropped.mk"

    export_host_relations(_contradicting_hosts(), tmp_path / "relations.mk", dropped_file)

    assert [(entry["hosts"], entry["sites"]) for entry in read_dropped_relations(dropped_file)] == [
        (["board", "os1"], ["central"])
    ]


def test_export_keeps_what_it_dropped_across_customers_from_their_sites(tmp_path: Path) -> None:
    """The message names both hosts, so neither customer's site may show it."""
    dropped_file = tmp_path / "dropped.mk"
    all_hosts = {
        HostName("board"): FakeHost(
            "board", [{"kind": "management", "direction": "parent", "host": "os1"}], site="site_a"
        ),
        HostName("os1"): FakeHost(
            "os1", [{"kind": "management", "direction": "parent", "host": "board"}], site="site_b"
        ),
    }

    export_host_relations(
        all_hosts,
        tmp_path / "relations.mk",
        dropped_file,
        customer_of_site={"site_a": "customer_a", "site_b": "customer_b"}.get,
    )

    assert read_dropped_relations(dropped_file) == []


def test_export_clears_what_it_dropped_once_the_pair_is_settled(tmp_path: Path) -> None:
    dropped_file = tmp_path / "dropped.mk"
    export_host_relations(_contradicting_hosts(), tmp_path / "relations.mk", dropped_file)

    export_host_relations(
        fake_hosts(board=[{"kind": "management", "direction": "parent", "host": "os1"}], os1=None),
        tmp_path / "relations.mk",
        dropped_file,
    )

    assert read_dropped_relations(dropped_file) == []


def test_a_site_is_told_what_was_dropped_on_its_hosts(tmp_path: Path) -> None:
    """Every activation, until an export without the problem replaces the file."""
    write_dropped_relations(
        tmp_path / "dropped.mk",
        [
            {
                "reason": "both_primary",
                "hosts": ["board", "os1"],
                "sites": ["here", "elsewhere"],
                "kind": "management",
                "direction": "parent",
            },
            {
                "reason": "unreadable",
                "hosts": ["broken"],
                "sites": ["elsewhere"],
                "error": "not a list",
            },
        ],
    )

    assert dropped_relations_of_site(tmp_path / "dropped.mk", "here") == [
        (
            "'board' and 'os1' both store themselves as 'Management board' of the other, so the "
            "monitoring shows neither relation. Save one of the two hosts in Setup to settle it."
        )
    ]


def test_a_site_is_told_which_host_has_relations_that_cannot_be_read(tmp_path: Path) -> None:
    write_dropped_relations(
        tmp_path / "dropped.mk",
        [{"reason": "unreadable", "hosts": ["broken"], "sites": ["here"], "error": "not a list"}],
    )

    assert dropped_relations_of_site(tmp_path / "dropped.mk", "here") == [
        "The relations of host 'broken' cannot be read and are left out: not a list"
    ]


def test_a_site_is_told_which_relation_only_the_os_host_stores(tmp_path: Path) -> None:
    write_dropped_relations(
        tmp_path / "dropped.mk",
        [{"reason": "primary_missing", "hosts": ["srv", "board"], "sites": ["here"]}],
    )

    assert dropped_relations_of_site(tmp_path / "dropped.mk", "here") == [
        (
            "'srv' stores a relation to 'board' that 'board' does not store, so the monitoring "
            "does not show it. Add it on 'board', or remove it from 'srv'."
        )
    ]


def test_a_site_is_not_told_what_this_version_cannot_word(tmp_path: Path) -> None:
    """A file left by another version must not stop the activation of the site."""
    write_dropped_relations(
        tmp_path / "dropped.mk",
        [
            {
                "reason": "both_primary",
                "hosts": ["a", "b"],
                "sites": ["here"],
                "kind": "kind_of_a_later_version",
                "direction": "parent",
            },
            {"reason": "unreadable", "hosts": ["broken"], "sites": ["here"], "error": "not a list"},
        ],
    )

    assert dropped_relations_of_site(tmp_path / "dropped.mk", "here") == [
        "The relations of host 'broken' cannot be read and are left out: not a list"
    ]


def test_a_site_is_told_nothing_before_the_first_export(tmp_path: Path) -> None:
    assert dropped_relations_of_site(tmp_path / "dropped.mk", "here") == []


@pytest.mark.parametrize(
    "all_hosts, hosts, entries",
    [
        pytest.param(
            fake_hosts(
                mgmt=[{"kind": "management", "direction": "parent", "host": "srv"}], srv=None
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
        export_host_relations(all_hosts, tmp_path / "relations.mk", tmp_path / "dropped.mk")

    summary = caplog.records[-1].args
    assert isinstance(summary, Mapping)
    assert summary["hosts"] == hosts
    assert summary["entries"] == entries
    assert str(summary["path"]).endswith("relations.mk")


@pytest.mark.usefixtures("with_admin_login", "load_config")
def test_activation_exports_the_relations() -> None:
    """Pins the wiring: the activation itself writes the export file, where config sync finds it."""
    ActivateChangesManager()._pre_activate_changes(  # noqa: SLF001
        make_folder_tree(Config()), SiteConfigurations({}), debug=True
    )

    assert RELATIONS_MACRO in relations_export_path().read_text()
    assert relations_dropped_path().exists()


def test_the_result_of_a_site_gets_what_was_dropped_on_its_hosts(tmp_path: Path) -> None:
    write_dropped_relations(
        tmp_path / "dropped.mk",
        [{"reason": "unreadable", "hosts": ["broken"], "sites": ["here"], "error": "not a list"}],
    )
    warnings = {"core": ["warning of the core"]}

    add_dropped_relations(warnings, "here", tmp_path / "dropped.mk")

    assert warnings == {
        "core": ["warning of the core"],
        DROPPED_RELATIONS_WARNING_KEY: [
            "The relations of host 'broken' cannot be read and are left out: not a list"
        ],
    }


def test_the_result_of_a_site_without_dropped_relations_stays_as_it_is(tmp_path: Path) -> None:
    warnings = {"core": ["warning of the core"]}

    add_dropped_relations(warnings, "here", tmp_path / "dropped.mk")

    assert warnings == {"core": ["warning of the core"]}


def _activate_remote_site_after_sync(monkeypatch: pytest.MonkeyPatch) -> Mapping[str, list[str]]:
    """Activate ``remote`` the way the central site does after syncing files to it.

    The automation call to the remote site is patched out: ``_do_activate`` makes it itself and
    offers no way to pass it in (technical debt of ``activate_changes``).
    """
    write_dropped_relations(
        relations_dropped_path(),
        [{"reason": "unreadable", "hosts": ["broken"], "sites": ["remote"], "error": "not a list"}],
    )
    monkeypatch.setattr(
        activate_changes,
        "_call_activate_changes_automation",
        lambda *args, **kwargs: {},  # noqa: ARG005
    )
    return activate_changes._do_activate(  # noqa: SLF001
        make_folder_tree(Config()),
        SiteId("remote"),
        RemoteAutomationConfig(
            site_id=SiteId("remote"),
            base_url="http://remote/check_mk/",
            secret="secret",
            insecure=False,
        ),
        [],
        SiteActivationState(
            _site_id=SiteId("remote"),
            _activation_id="",
            _phase=None,
            _state=None,
            _status_text=None,
            _status_details=None,
            _time_started=0.0,
            _time_updated=None,
            _time_ended=None,
            _expected_duration=0.0,
            _pid=0,
            _user_id=None,
            _source=None,
        ),
        debug=True,
        is_remote_site=True,
    )


@pytest.mark.usefixtures("load_config")
def test_the_central_site_adds_what_was_dropped_to_the_result_of_a_synced_remote_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _activate_remote_site_after_sync(monkeypatch) == {
        DROPPED_RELATIONS_WARNING_KEY: [
            "The relations of host 'broken' cannot be read and are left out: not a list"
        ]
    }


@pytest.mark.usefixtures("load_config", "remote_site")
def test_a_remote_site_adds_nothing_to_the_results_it_builds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _activate_remote_site_after_sync(monkeypatch) == {}


@pytest.fixture
def unwritable_relations_export() -> Iterator[None]:
    export_file = relations_export_path()
    export_file.mkdir(parents=True)
    yield
    export_file.rmdir()


@pytest.mark.usefixtures("with_admin_login", "load_config", "unwritable_relations_export")
def test_activation_goes_on_when_the_relations_cannot_be_exported() -> None:
    ActivateChangesManager()._pre_activate_changes(  # noqa: SLF001
        make_folder_tree(Config()), SiteConfigurations({}), debug=False
    )


@pytest.mark.usefixtures("with_admin_login", "load_config", "unwritable_relations_export")
def test_a_failed_export_is_logged_as_host_relations(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR, logger="cmk.web.host_relations"):
        ActivateChangesManager()._pre_activate_changes(  # noqa: SLF001
            make_folder_tree(Config()), SiteConfigurations({}), debug=False
        )

    assert any(record.name == "cmk.web.host_relations" for record in caplog.records)
