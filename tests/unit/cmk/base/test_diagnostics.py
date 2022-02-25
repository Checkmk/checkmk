#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import shutil
from pathlib import Path
from typing import NamedTuple

import pytest
import requests

import livestatus

import cmk.utils.packaging as packaging
import cmk.utils.paths

import cmk.base.diagnostics as diagnostics


@pytest.fixture()
def _fake_local_connection(host_list):
    def _wrapper(host_list):
        class FakeLocalConnection:
            def query(self, query):
                return host_list

        return FakeLocalConnection

    return _wrapper


@pytest.fixture()
def _collectors():
    return diagnostics.Collectors()


#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def test_diagnostics_dump_elements():
    fixed_element_classes = set(
        [
            diagnostics.GeneralDiagnosticsElement,
        ]
    )
    element_classes = set(type(e) for e in diagnostics.DiagnosticsDump().elements)
    assert fixed_element_classes.issubset(element_classes)


def test_diagnostics_dump_create():
    diagnostics_dump = diagnostics.DiagnosticsDump()
    diagnostics_dump._create_dump_folder()

    assert isinstance(diagnostics_dump.dump_folder, Path)

    assert diagnostics_dump.dump_folder.exists()
    assert diagnostics_dump.dump_folder.name == "diagnostics"

    diagnostics_dump._create_tarfile()

    tarfiles = diagnostics_dump.dump_folder.iterdir()
    assert len(list(tarfiles)) == 1
    assert all(tarfile.suffix == ".tar.gz" for tarfile in tarfiles)


def test_diagnostics_cleanup_dump_folder():
    diagnostics_dump = diagnostics.DiagnosticsDump()
    diagnostics_dump._create_dump_folder()

    # Fake existing tarfiles
    for nr in range(10):
        diagnostics_dump.dump_folder.joinpath("dummy-%s.tar.gz" % nr).touch()

    diagnostics_dump._cleanup_dump_folder()

    tarfiles = diagnostics_dump.dump_folder.iterdir()
    assert len(list(tarfiles)) == diagnostics_dump._keep_num_dumps
    assert all(tarfile.suffix == ".tar.gz" for tarfile in tarfiles)


# .
#   .--elements------------------------------------------------------------.
#   |                   _                           _                      |
#   |               ___| | ___ _ __ ___   ___ _ __ | |_ ___                |
#   |              / _ \ |/ _ \ '_ ` _ \ / _ \ '_ \| __/ __|               |
#   |             |  __/ |  __/ | | | | |  __/ | | | |_\__ \               |
#   |              \___|_|\___|_| |_| |_|\___|_| |_|\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_diagnostics_element_general():
    diagnostics_element = diagnostics.GeneralDiagnosticsElement()
    assert diagnostics_element.ident == "general"
    assert diagnostics_element.title == "General"
    assert diagnostics_element.description == (
        "OS, Checkmk version and edition, Time, Core, " "Python version and paths, Architecture"
    )


def test_diagnostics_element_general_content(tmp_path, _collectors):
    diagnostics_element = diagnostics.GeneralDiagnosticsElement()
    tmppath = Path(tmp_path).joinpath("tmp")
    filepath = next(diagnostics_element.add_or_get_files(tmppath, _collectors))

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("general.json")

    info_keys = [
        "time",
        "time_human_readable",
        "os",
        "version",
        "edition",
        "core",
        "python_version",
        "python_paths",
        "arch",
    ]
    content = json.loads(filepath.open().read())

    assert sorted(content.keys()) == sorted(info_keys)


def test_diagnostics_element_local_files():
    diagnostics_element = diagnostics.LocalFilesDiagnosticsElement()
    assert diagnostics_element.ident == "local_files"
    assert diagnostics_element.title == "Local Files"
    assert diagnostics_element.description == (
        "List of installed, unpacked, optional files below $OMD_ROOT/local. "
        "This also includes information about installed MKPs."
    )


def test_diagnostics_element_local_files_content(tmp_path, _collectors):
    diagnostics_element = diagnostics.LocalFilesDiagnosticsElement()

    def create_test_package(name):
        check_dir = cmk.utils.paths.local_checks_dir
        check_dir.mkdir(parents=True, exist_ok=True)

        with check_dir.joinpath(name).open("w", encoding="utf-8") as f:
            f.write("test-check\n")

        package_info = packaging.get_initial_package_info(name)
        package_info["files"] = {
            "checks": [name],
        }

        packaging.create(package_info)

    packaging.package_dir().mkdir(parents=True, exist_ok=True)
    name = "test-package"
    create_test_package(name)

    tmppath = Path(tmp_path).joinpath("tmp")
    filepath = next(diagnostics_element.add_or_get_files(tmppath, _collectors))

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("local_files.json")

    info_keys = [
        "installed",
        "unpackaged",
        "parts",
        "optional_packages",
        "disabled_packages",
    ]
    content = json.loads(filepath.open().read())

    assert sorted(content.keys()) == sorted(info_keys)

    installed_keys = [name]
    assert sorted(content["installed"].keys()) == sorted(installed_keys)
    assert content["installed"][name]["files"] == {"checks": [name]}

    unpackaged_keys = [
        "agent_based",
        "agents",
        "alert_handlers",
        "bin",
        "checkman",
        "checks",
        "doc",
        "ec_rule_packs",
        "inventory",
        "lib",
        "locales",
        "mibs",
        "notifications",
        "pnp-templates",
        "web",
        "gui",
    ]
    assert sorted(content["unpackaged"].keys()) == sorted(unpackaged_keys)
    for key in unpackaged_keys:
        assert content["unpackaged"][key] == []

    parts_keys = [
        "agent_based",
        "agents",
        "alert_handlers",
        "bin",
        "checkman",
        "checks",
        "doc",
        "ec_rule_packs",
        "inventory",
        "lib",
        "locales",
        "mibs",
        "notifications",
        "pnp-templates",
        "web",
        "gui",
    ]
    assert sorted(content["parts"].keys()) == sorted(parts_keys)
    part_keys = [
        "files",
        "path",
        "permissions",
        "title",
    ]
    for key in parts_keys:
        assert sorted(content["parts"][key].keys()) == sorted(part_keys)
        if key == "checks":
            assert content["parts"][key]["files"] == [name]
            assert content["parts"][key]["permissions"] == [420]
        else:
            assert content["parts"][key]["files"] == []
            assert content["parts"][key]["permissions"] == []

    assert content["optional_packages"] == {}

    shutil.rmtree(str(packaging.package_dir()))


def test_diagnostics_element_omd_config():
    diagnostics_element = diagnostics.OMDConfigDiagnosticsElement()
    assert diagnostics_element.ident == "omd_config"
    assert diagnostics_element.title == "OMD Config"
    assert diagnostics_element.description == (
        "Apache mode and TCP address and port, Core, "
        "Liveproxy daemon and livestatus TCP mode, "
        "Event daemon config, Multiste authorisation, "
        "NSCA mode, TMP filesystem mode"
    )


def test_diagnostics_element_omd_config_content(tmp_path, _collectors):
    diagnostics_element = diagnostics.OMDConfigDiagnosticsElement()

    # Fake raw output of site.conf
    etc_omd_dir = cmk.utils.paths.omd_root / "etc" / "omd"
    etc_omd_dir.mkdir(parents=True, exist_ok=True)
    with etc_omd_dir.joinpath("site.conf").open("w") as f:
        f.write(
            """CONFIG_ADMIN_MAIL=''
CONFIG_APACHE_MODE='own'
CONFIG_APACHE_TCP_ADDR='127.0.0.1'
CONFIG_APACHE_TCP_PORT='5000'
CONFIG_AUTOSTART='off'
CONFIG_CORE='cmc'
CONFIG_LIVEPROXYD='on'
CONFIG_LIVESTATUS_TCP='off'
CONFIG_LIVESTATUS_TCP_ONLY_FROM='0.0.0.0 ::/0'
CONFIG_LIVESTATUS_TCP_PORT='6557'
CONFIG_LIVESTATUS_TCP_TLS='on'
CONFIG_MKEVENTD='on'
CONFIG_MKEVENTD_SNMPTRAP='off'
CONFIG_MKEVENTD_SYSLOG='on'
CONFIG_MKEVENTD_SYSLOG_TCP='off'
CONFIG_MULTISITE_AUTHORISATION='on'
CONFIG_MULTISITE_COOKIE_AUTH='on'
CONFIG_NAGIOS_THEME='classicui'
CONFIG_NSCA='off'
CONFIG_NSCA_TCP_PORT='5667'
CONFIG_PNP4NAGIOS='on'
CONFIG_TMPFS='on'"""
        )

    tmppath = Path(tmp_path).joinpath("tmp")
    filepath = next(diagnostics_element.add_or_get_files(tmppath, _collectors))

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("omd_config.json")

    info_keys = [
        "CONFIG_ADMIN_MAIL",
        "CONFIG_APACHE_MODE",
        "CONFIG_APACHE_TCP_ADDR",
        "CONFIG_APACHE_TCP_PORT",
        "CONFIG_AUTOSTART",
        "CONFIG_CORE",
        "CONFIG_LIVEPROXYD",
        "CONFIG_LIVESTATUS_TCP",
        "CONFIG_LIVESTATUS_TCP_ONLY_FROM",
        "CONFIG_LIVESTATUS_TCP_PORT",
        "CONFIG_LIVESTATUS_TCP_TLS",
        "CONFIG_MKEVENTD",
        "CONFIG_MKEVENTD_SNMPTRAP",
        "CONFIG_MKEVENTD_SYSLOG",
        "CONFIG_MKEVENTD_SYSLOG_TCP",
        "CONFIG_MULTISITE_AUTHORISATION",
        "CONFIG_MULTISITE_COOKIE_AUTH",
        "CONFIG_NAGIOS_THEME",
        "CONFIG_NSCA",
        "CONFIG_NSCA_TCP_PORT",
        "CONFIG_PNP4NAGIOS",
        "CONFIG_TMPFS",
    ]
    content = json.loads(filepath.open().read())

    assert sorted(content.keys()) == sorted(info_keys)
    for key, value in zip(
        info_keys,
        [
            "",
            "own",
            "127.0.0.1",
            "5000",
            "off",
            "cmc",
            "on",
            "off",
            "0.0.0.0 ::/0",
            "6557",
            "on",
            "on",
            "off",
            "on",
            "off",
            "on",
            "on",
            "classicui",
            "off",
            "5667",
            "on",
            "on",
        ],
    ):
        assert content[key] == value

    shutil.rmtree(str(etc_omd_dir))


def test_diagnostics_element_checkmk_overview():
    diagnostics_element = diagnostics.CheckmkOverviewDiagnosticsElement()
    assert diagnostics_element.ident == "checkmk_overview"
    assert diagnostics_element.title == "Checkmk Overview of Checkmk Server"
    assert diagnostics_element.description == (
        "Checkmk Agent, Number, version and edition of sites, Cluster host; "
        "Number of hosts, services, CMK Helper, Live Helper, "
        "Helper usage; State of daemons: Apache, Core, Crontag, "
        "DCD, Liveproxyd, MKEventd, MKNotifyd, RRDCached "
        "(Agent plugin mk_inventory needs to be installed)"
    )


@pytest.mark.parametrize(
    "host_list, host_tree, error",
    [
        ([], None, "No Checkmk server found"),
        ([["checkmk-server-name"]], None, "No HW/SW inventory tree of 'checkmk-server-name' found"),
        (
            [["checkmk-server-name"]],
            {
                "hardware": {},
                "networking": {},
                "software": {
                    "applications": {},
                },
            },
            "No HW/SW inventory node 'Software > Applications > Checkmk'",
        ),
    ],
)
def test_diagnostics_element_checkmk_overview_error(
    monkeypatch, tmp_path, _fake_local_connection, _collectors, host_list, host_tree, error
):
    diagnostics_element = diagnostics.CheckmkOverviewDiagnosticsElement()

    monkeypatch.setattr(livestatus, "LocalConnection", _fake_local_connection(host_list))

    if host_tree:
        # Fake HW/SW inventory tree
        inventory_dir = Path(cmk.utils.paths.inventory_output_dir)
        inventory_dir.mkdir(parents=True, exist_ok=True)
        with inventory_dir.joinpath("checkmk-server-name").open("w") as f:
            f.write(repr(host_tree))

    tmppath = Path(tmp_path).joinpath("tmp")

    with pytest.raises(diagnostics.DiagnosticsElementError) as e:
        next(diagnostics_element.add_or_get_files(tmppath, _collectors))
        assert error == str(e)

    if host_tree:
        shutil.rmtree(str(inventory_dir))


@pytest.mark.parametrize(
    "host_list, host_tree",
    [
        (
            [["checkmk-server-name"]],
            {
                "hardware": {},
                "networking": {},
                "software": {
                    "applications": {
                        "check_mk": {
                            "versions": [
                                {
                                    "version": "2020.06.07.cee",
                                    "number": "2020.06.07",
                                    "edition": "cee",
                                    "demo": False,
                                    "num_sites": 0,
                                },
                                {
                                    "version": "2020.06.09.cee",
                                    "number": "2020.06.09",
                                    "edition": "cee",
                                    "demo": False,
                                    "num_sites": 1,
                                },
                            ],
                            "sites": [
                                {
                                    "site": "heute",
                                    "used_version": "2020.06.09.cee",
                                    "autostart": False,
                                }
                            ],
                            "cluster": {"is_cluster": False},
                            "agent_version": "1.7.0i1",
                            "num_versions": 2,
                            "num_sites": 1,
                        }
                    }
                },
            },
        ),
    ],
)
def test_diagnostics_element_checkmk_overview_content(
    monkeypatch, tmp_path, _fake_local_connection, _collectors, host_list, host_tree
):

    diagnostics_element = diagnostics.CheckmkOverviewDiagnosticsElement()

    monkeypatch.setattr(livestatus, "LocalConnection", _fake_local_connection(host_list))

    if host_tree:
        # Fake HW/SW inventory tree
        inventory_dir = Path(cmk.utils.paths.inventory_output_dir)
        inventory_dir.mkdir(parents=True, exist_ok=True)
        with inventory_dir.joinpath("checkmk-server-name").open("w") as f:
            f.write(repr(host_tree))

    tmppath = Path(tmp_path).joinpath("tmp")
    filepath = next(diagnostics_element.add_or_get_files(tmppath, _collectors))

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("checkmk_overview.json")

    content = json.loads(filepath.open().read())

    assert content["Nodes"]["cluster"]["Attributes"]["Pairs"] == {
        "is_cluster": False,
    }

    assert content["Nodes"]["sites"]["Table"]["Rows"] == [
        {
            "autostart": False,
            "site": "heute",
            "used_version": "2020.06.09.cee",
        },
    ]

    assert content["Nodes"]["versions"]["Table"]["Rows"] == [
        {
            "demo": False,
            "edition": "cee",
            "num_sites": 0,
            "number": "2020.06.07",
            "version": "2020.06.07.cee",
        },
        {
            "demo": False,
            "edition": "cee",
            "num_sites": 1,
            "number": "2020.06.09",
            "version": "2020.06.09.cee",
        },
    ]

    shutil.rmtree(str(inventory_dir))


@pytest.mark.parametrize(
    "diag_elem, ident, title, description",
    [
        (
            diagnostics.CheckmkConfigFilesDiagnosticsElement,
            "checkmk_config_files",
            "Checkmk Configuration Files",
            "Configuration files ('*.mk' or '*.conf') from etc/checkmk:",
        ),
        (
            diagnostics.CheckmkLogFilesDiagnosticsElement,
            "checkmk_log_files",
            "Checkmk Log Files",
            "Log files ('*.log' or '*.state') from var/log:",
        ),
    ],
)
def test_diagnostics_element_checkmk_files(diag_elem, ident, title, description):
    files = ["/path/to/raw-conf-file1", "/path/to/raw-conf-file2"]
    diagnostics_element = diag_elem(files)
    assert diagnostics_element.ident == ident
    assert diagnostics_element.title == title
    assert diagnostics_element.description == ("%s %s" % (description, ", ".join(files)))


@pytest.mark.parametrize(
    "diag_elem",
    [
        diagnostics.CheckmkConfigFilesDiagnosticsElement,
        diagnostics.CheckmkLogFilesDiagnosticsElement,
    ],
)
def test_diagnostics_element_checkmk_files_error(tmp_path, _collectors, diag_elem):
    short_test_conf_filepath = "/no/such/file"
    diagnostics_element = diag_elem([short_test_conf_filepath])
    tmppath = Path(tmp_path).joinpath("tmp")

    with pytest.raises(diagnostics.DiagnosticsElementError) as e:
        next(diagnostics_element.add_or_get_files(tmppath, _collectors))
        assert "No such files %s" % short_test_conf_filepath == str(e)


@pytest.mark.parametrize(
    "diag_elem, test_dir, test_filename",
    [
        (
            diagnostics.CheckmkConfigFilesDiagnosticsElement,
            cmk.utils.paths.default_config_dir,
            "test.conf",
        ),
        (diagnostics.CheckmkLogFilesDiagnosticsElement, cmk.utils.paths.log_dir, "test.log"),
    ],
)
def test_diagnostics_element_checkmk_files_content(
    tmp_path, _collectors, diag_elem, test_dir, test_filename
):
    test_conf_dir = Path(test_dir) / "test"
    test_conf_dir.mkdir(parents=True, exist_ok=True)
    test_conf_filepath = test_conf_dir.joinpath(test_filename)
    with test_conf_filepath.open("w", encoding="utf-8") as f:
        f.write("testvar = testvalue")

    short_test_conf_filepath = str(Path(test_conf_filepath).relative_to(test_dir))
    diagnostics_element = diag_elem([short_test_conf_filepath])
    tmppath = Path(tmp_path).joinpath("tmp")
    tmppath.mkdir(parents=True, exist_ok=True)
    filepath = next(diagnostics_element.add_or_get_files(tmppath, _collectors))

    assert filepath == tmppath.joinpath("test-%s" % test_filename)

    with filepath.open("r", encoding="utf-8") as f:
        content = f.read()

    assert content == "testvar = testvalue"


def test_diagnostics_element_performance_graphs():
    diagnostics_element = diagnostics.PerformanceGraphsDiagnosticsElement()
    assert diagnostics_element.ident == "performance_graphs"
    assert diagnostics_element.title == "Performance Graphs of Checkmk Server"
    assert diagnostics_element.description == (
        "CPU load and utilization, Number of threads, Kernel Performance, "
        "OMD, Filesystem, Apache Status, TCP Connections of the time ranges "
        "25 hours and 35 days"
    )


@pytest.mark.parametrize(
    "host_list, status_code, text, content, error",
    [
        # no Checkmk server
        ([], 123, "", b"", "No Checkmk server found"),
        ([], 200, "<html>foo bar</html>", b"", "No Checkmk server found"),
        ([], 200, "", b"", "No Checkmk server found"),
        ([], 200, "", b"%PDF-", "No Checkmk server found"),
        # Checkmk server
        ([["checkmk-server-name"]], 123, "", b"", "HTTP error - 123 ()"),
        (
            [["checkmk-server-name"]],
            200,
            "<html>foo bar</html>",
            b"",
            "Login failed - Invalid automation user or secret",
        ),
        ([["checkmk-server-name"]], 200, "", b"", "Verification of PDF document header failed"),
    ],
)
def test_diagnostics_element_performance_graphs_error(
    monkeypatch,
    tmp_path,
    _fake_local_connection,
    _collectors,
    host_list,
    status_code,
    text,
    content,
    error,
):

    diagnostics_element = diagnostics.PerformanceGraphsDiagnosticsElement()

    monkeypatch.setattr(livestatus, "LocalConnection", _fake_local_connection(host_list))

    class FakeResponse(NamedTuple):
        status_code: int
        text: str
        content: str

    monkeypatch.setattr(
        requests, "post", lambda *arg, **kwargs: FakeResponse(status_code, text, content)
    )

    automation_dir = Path(cmk.utils.paths.var_dir) / "web" / "automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    with automation_dir.joinpath("automation.secret").open("w") as f:
        f.write("my-123-password")

    etc_omd_dir = cmk.utils.paths.omd_root / "etc" / "omd"
    etc_omd_dir.mkdir(parents=True, exist_ok=True)
    with etc_omd_dir.joinpath("site.conf").open("w") as f:
        f.write(
            """CONFIG_APACHE_TCP_ADDR='127.0.0.1'
CONFIG_APACHE_TCP_PORT='5000'"""
        )

    tmppath = Path(tmp_path).joinpath("tmp")
    tmppath.mkdir(parents=True, exist_ok=True)

    with pytest.raises(diagnostics.DiagnosticsElementError) as e:
        next(diagnostics_element.add_or_get_files(tmppath, _collectors))
        assert error == str(e)

    shutil.rmtree(str(automation_dir))
    shutil.rmtree(str(etc_omd_dir))


@pytest.mark.parametrize(
    "host_list, status_code, text, content",
    [
        ([["checkmk-server-name"]], 200, "", b"%PDF-"),
    ],
)
def test_diagnostics_element_performance_graphs_content(
    monkeypatch,
    tmp_path,
    _fake_local_connection,
    _collectors,
    host_list,
    status_code,
    text,
    content,
):

    diagnostics_element = diagnostics.PerformanceGraphsDiagnosticsElement()

    monkeypatch.setattr(livestatus, "LocalConnection", _fake_local_connection(host_list))

    class FakeResponse(NamedTuple):
        status_code: int
        text: str
        content: str

    monkeypatch.setattr(
        requests, "post", lambda *arg, **kwargs: FakeResponse(status_code, text, content)
    )

    automation_dir = Path(cmk.utils.paths.var_dir) / "web" / "automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    with automation_dir.joinpath("automation.secret").open("w") as f:
        f.write("my-123-password")

    etc_omd_dir = cmk.utils.paths.omd_root / "etc" / "omd"
    etc_omd_dir.mkdir(parents=True, exist_ok=True)
    with etc_omd_dir.joinpath("site.conf").open("w") as f:
        f.write(
            """CONFIG_APACHE_TCP_ADDR='127.0.0.1'
CONFIG_APACHE_TCP_PORT='5000'"""
        )

    tmppath = Path(tmp_path).joinpath("tmp")
    tmppath.mkdir(parents=True, exist_ok=True)
    filepath = next(diagnostics_element.add_or_get_files(tmppath, _collectors))

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("performance_graphs.pdf")

    shutil.rmtree(str(automation_dir))
    shutil.rmtree(str(etc_omd_dir))
