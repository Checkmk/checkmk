#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import csv
import json
import os
import shutil
import uuid
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NamedTuple
from unittest.mock import mock_open, patch

import pytest
import requests

import livestatus

import cmk.utils.paths
from cmk.base import diagnostics
from cmk.ccc.hostaddress import HostName
from cmk.ccc.version import Edition
from cmk.crash import make_crash_report_base_path
from cmk.inventory.structured_data import (
    deserialize_tree,
    InventoryStore,
    make_meta,
    SDRawTree,
)
from tests.testlib.common.empty_config import EMPTY_CONFIG


def _diagnostics_elements() -> Sequence[diagnostics.ABCDiagnosticsElement]:
    return diagnostics.diagnostics_elements_for(
        edition=Edition.COMMUNITY,
        loaded_config=EMPTY_CONFIG,
        core_performance_settings=lambda x: {},
        omd_config={},
        parameters={},
    )


@pytest.fixture(autouse=True)
def reset_collector_caches() -> None:
    # diagnostics.get_omd_config.cache_clear()
    diagnostics.verify_checkmk_server_host.cache_clear()


@pytest.fixture()
def _fake_local_connection(host_list: Sequence[Sequence[str]]) -> Callable:
    class FakeLocalConnection:
        def query(self, query: str) -> Sequence[Sequence[str]]:
            return host_list

    def _wrapper(host_list: Sequence[Sequence[str]]) -> type[FakeLocalConnection]:
        return FakeLocalConnection

    return _wrapper


#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def test_diagnostics_dump_elements() -> None:
    fixed_element_classes = {
        diagnostics.GeneralDiagnosticsElement,
    }
    element_classes = {type(e) for e in _diagnostics_elements()}
    assert fixed_element_classes.issubset(element_classes)


@pytest.mark.usefixtures("mock_livestatus")
def test_diagnostics_dump_create(tmp_path: Path) -> None:
    elements = _diagnostics_elements()
    diagnostics_dump = diagnostics.DiagnosticsDump(
        elements=elements,
        diagnostics_dir=tmp_path / "var/check_mk/diagnostics",
        omd_root=tmp_path,
    )
    diagnostics_dump._create_dump_folder()

    assert isinstance(diagnostics_dump.dump_folder, Path)

    assert diagnostics_dump.dump_folder.exists()
    assert diagnostics_dump.dump_folder.name == "diagnostics"

    diagnostics_dump._create_tarfile(elements, tmp_path)

    tarfiles = diagnostics_dump.dump_folder.iterdir()
    assert len(list(tarfiles)) == 1
    assert all(tarfile.suffix == ".tar.gz" for tarfile in tarfiles)


def test_diagnostics_cleanup_dump_folder(tmp_path: Path) -> None:
    elements = _diagnostics_elements()
    diagnostics_dump = diagnostics.DiagnosticsDump(
        elements=elements,
        diagnostics_dir=tmp_path / "var/check_mk/diagnostics",
        omd_root=tmp_path,
    )
    diagnostics_dump._create_dump_folder()

    # Fake existing tarfiles
    for nr in range(10):
        diagnostics_dump.dump_folder.joinpath("dummy-%s.tar.gz" % nr).touch()

    diagnostics_dump._cleanup_dump_folder(tmp_path)

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


def test_diagnostics_element_general() -> None:
    diagnostics_element = diagnostics.GeneralDiagnosticsElement()
    assert diagnostics_element.title == "General"
    assert diagnostics_element.description == (
        "OS, Checkmk version and edition, Time, Core, Python version and paths, Architecture"
    )
    assert diagnostics_element.filename == "general.json"


@pytest.mark.usefixtures("patch_omd_site")
def test_diagnostics_element_general_content(tmp_path: Path) -> None:
    diagnostics_element = diagnostics.GeneralDiagnosticsElement()
    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)
    filepath = next(
        diagnostics_element.add_or_get_files(
            omd_root=cmk.utils.paths.omd_root, tmp_dump_folder=tmp_dump_folder
        )
    )

    assert isinstance(tmp_path, Path)
    assert isinstance(filepath, Path)
    assert filepath == tmp_dump_folder.joinpath("general.json")

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


def test_diagnostics_element_perfdata() -> None:
    diagnostics_element = diagnostics.PerfDataDiagnosticsElement(
        EMPTY_CONFIG,
        core_performance_settings=lambda x: {},
    )
    assert diagnostics_element.filename == "perfdata.json"
    assert diagnostics_element.title == "Metrics"
    assert diagnostics_element.description == (
        "Metrics related to sizing, e.g. number of helpers, hosts, services"
    )


def test_diagnostics_element_hw_info(tmp_path: Path) -> None:
    proc_path = tmp_path.joinpath("proc")
    proc_path.mkdir(exist_ok=True)

    # Create three fake proc files
    with open(proc_path / "meminfo", "w", encoding="utf-8") as f:
        f.write("MemTotal:       32663516 kB")

    with open(proc_path / "loadavg", "w", encoding="utf-8") as f:
        f.write("1.19 1.58 1.75 2/1922 891074")

    with open(proc_path / "cpuinfo", "w", encoding="utf-8") as f:
        f.write("""processor : 0
physical id : 0
processor   : 1
physical id : 0
processor   : 2
physical id : 0
processor   : 3
physical id : 0""")

    diagnostics_element = diagnostics.HWDiagnosticsElement(proc_path)
    infos = diagnostics_element.contents(tmp_path.joinpath("omd_root"))

    assert diagnostics_element.title == "HW Information"
    assert diagnostics_element.description == ("Hardware information of the Checkmk server")
    assert diagnostics_element.filename == "hwinfo.json"
    assert json.loads(infos) == {
        "meminfo": {"MemTotal": "32663516 kB"},
        "loadavg": {"loadavg_1": "1.19", "loadavg_5": "1.58", "loadavg_15": "1.75"},
        "cpuinfo": {"physical_id": "0", "num_logical_processors": "4", "cpus": 1},
    }


def test_diagnostics_element_vendor_info(tmp_path: Path) -> None:
    dmi_id_path = tmp_path.joinpath("sys/class/dmi/id")
    dmi_id_path.mkdir(parents=True, exist_ok=True)

    # Create five fake sys files
    with open(dmi_id_path / "bios_vendor", "w", encoding="utf-8") as f:
        f.write("Dull Ink")

    with open(dmi_id_path / "bios_version", "w", encoding="utf-8") as f:
        f.write("1.2.3")

    with open(dmi_id_path / "sys_vendor", "w", encoding="utf-8") as f:
        f.write("Dull Ink")

    with open(dmi_id_path / "product_name", "w", encoding="utf-8") as f:
        f.write("Longitude 4")

    with open(dmi_id_path / "chassis_asset_tag", "w", encoding="utf-8") as f:
        f.write("")

    diagnostics_element = diagnostics.VendorDiagnosticsElement(dmi_id_path)
    infos = diagnostics_element.contents(tmp_path.joinpath("omd_root"))

    assert diagnostics_element.title == "Vendor Information"
    assert diagnostics_element.description == ("HW vendor information of the Checkmk server")
    assert diagnostics_element.filename == "vendorinfo.json"
    assert json.loads(infos) == {
        "bios_vendor": "Dull Ink",
        "bios_version": "1.2.3",
        "chassis_asset_tag": "Other",
        "product_name": "Longitude 4",
        "sys_vendor": "Dull Ink",
    }


def test_diagnostics_element_environment() -> None:
    diagnostics_element = diagnostics.EnvironmentDiagnosticsElement()
    assert diagnostics_element.title == "Environment Variables"
    assert diagnostics_element.description == ("Variables set in the site user's environment")
    assert diagnostics_element.filename == "environment.json"


def test_diagnostics_element_environment_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    environment_vars = {"France": "Paris", "Italy": "Rome", "Germany": "Berlin"}

    with monkeypatch.context() as m:
        for key, value in environment_vars.items():
            m.setenv(key, value)

        diagnostics_element = diagnostics.EnvironmentDiagnosticsElement()
        tmp_dump_folder = tmp_path.joinpath("tmp")
        tmp_dump_folder.mkdir(parents=True, exist_ok=True)
        filepath = next(
            diagnostics_element.add_or_get_files(omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder)
        )

        assert isinstance(filepath, Path)
        assert filepath == tmp_dump_folder.joinpath("environment.json")

        content = json.loads(filepath.open().read())
        assert "France" in content

        for key, value in environment_vars.items():
            assert content[key] == value

        assert content["OMD_SITE"] == cmk.ccc.site.omd_site()


def test_diagnostics_element_filesize() -> None:
    diagnostics_element = diagnostics.FilesSizeCSVDiagnosticsElement()
    assert diagnostics_element.title == "File Size"
    assert diagnostics_element.description == ("List of all files in the site including their size")
    assert diagnostics_element.filename == "file_size.csv"


@pytest.mark.usefixtures("monkeypatch")
def test_diagnostics_element_filesize_content(tmp_path: Path) -> None:
    omd_root = tmp_path.joinpath("omd_root")
    diagnostics_element = diagnostics.FilesSizeCSVDiagnosticsElement()

    test_dir = omd_root.joinpath("local/share/check_mk/checks")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir.joinpath("testfile")
    test_content = "test\n"
    test_group = "dummygroup"
    with test_file.open("w", encoding="utf-8") as f:
        f.write(test_content)

    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)
    with patch("pathlib.Path.group", return_value=test_group):
        filepath = next(
            diagnostics_element.add_or_get_files(omd_root=omd_root, tmp_dump_folder=tmp_dump_folder)
        )

    assert isinstance(filepath, Path)
    assert filepath == tmp_dump_folder.joinpath("file_size.csv")

    column_headers = [
        "path",
        "size",
        "owner",
        "group",
        "mode",
        "changed",
    ]

    size_of = {}
    group_of = {}
    last_row = {}
    with open(filepath, newline="") as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter=";", quotechar="'")
        for row in csvreader:
            size_of[row["path"]] = row["size"]
            group_of[row["path"]] = row["group"]
            last_row = row

    assert sorted(last_row.keys()) == sorted(column_headers)
    assert str(test_file) in size_of
    assert size_of[str(test_file)] == str(len(test_content))
    assert group_of[str(test_file)] == test_group


def test_diagnostics_element_dpkg() -> None:
    diagnostics_element = diagnostics.DpkgCSVDiagnosticsElement()
    assert diagnostics_element.title == "Dpkg packages information"
    assert diagnostics_element.description == (
        "Output of `dpkg -l`. See the corresponding command line help for more details."
    )
    assert diagnostics_element.filename == "dpkg_packages.csv"


@pytest.mark.usefixtures("monkeypatch")
def test_diagnostics_element_filesize_content_ignores_temporary_file(tmp_path: Path) -> None:
    omd_root = tmp_path.joinpath("omd_root")
    diagnostics_element = diagnostics.FilesSizeCSVDiagnosticsElement()

    # test_dir = cmk.utils.paths.local_checks_dir
    test_dir = omd_root.joinpath("local/share/check_mk/checks")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_dir.joinpath("testfile").write_text("test\n")

    test_dir.joinpath(".session_info.mk.newodhsmg3r").write_text("test\n")

    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)
    with patch("pathlib.Path.group", return_value="dummygroup"):
        filepath = next(
            diagnostics_element.add_or_get_files(omd_root=omd_root, tmp_dump_folder=tmp_dump_folder)
        )

    with open(filepath, newline="") as csvfile:
        files = [
            Path(row["path"]).name for row in csv.DictReader(csvfile, delimiter=";", quotechar="'")
        ]

    assert files == ["testfile"]


def test_diagnostics_element_dpkg_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    omd_root = tmp_path.joinpath("omd_root")
    test_bin_dir = omd_root.joinpath("bin")
    test_bin_dir.mkdir(parents=True, exist_ok=True)
    test_bin_filepath = test_bin_dir.joinpath("dpkg")

    with test_bin_filepath.open("w", encoding="utf-8") as f:
        f.write(
            """#!/bin/bash
                echo "Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name                                                        Version                                         Architecture Description
+++-===========================================================-===============================================-============-=====================================================================================================
ii  accountsservice                                             22.07.5-2ubuntu1.5                              amd64        query and manipulate user account information"
                """
        )

    os.chmod(test_bin_filepath, 0o770)

    with monkeypatch.context() as m:
        m.setenv("PATH", str(test_bin_dir))

        diagnostics_element = diagnostics.DpkgCSVDiagnosticsElement()
        tmp_dump_folder = tmp_path.joinpath("tmp")
        tmp_dump_folder.mkdir(parents=True, exist_ok=True)
        filepath = next(
            diagnostics_element.add_or_get_files(omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder)
        )

        assert isinstance(filepath, Path)
        assert filepath == tmp_dump_folder.joinpath("dpkg_packages.csv")

        content = filepath.open().read()

        assert "22.07.5-2ubuntu1.5" in content

        shutil.rmtree(str(test_bin_dir))


def test_diagnostics_element_rpm() -> None:
    diagnostics_element = diagnostics.RpmCSVDiagnosticsElement()
    assert diagnostics_element.title == "Rpm packages information"
    assert diagnostics_element.description == (
        "Output of `rpm -qa`. See the corresponding command line help for more details."
    )
    assert diagnostics_element.filename == "rpm_packages.csv"


def test_diagnostics_element_rpm_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    omd_root = tmp_path.joinpath("omd_root")
    test_bin_dir = omd_root.joinpath("bin")
    test_bin_dir.mkdir(parents=True, exist_ok=True)
    test_bin_filepath = test_bin_dir.joinpath("rpm")

    with test_bin_filepath.open("w", encoding="utf-8") as f:
        f.write(
            """#!/bin/bash
                echo "libgcc;11.4.1;2.1.el9;x86_64
crypto-policies;20230731;1.git94f0e2c.el9_3.1;noarch
tzdata;2023c;1.el9;noarch"
                """
        )

    os.chmod(test_bin_filepath, 0o770)

    with monkeypatch.context() as m:
        m.setenv("PATH", str(test_bin_dir))

        diagnostics_element = diagnostics.RpmCSVDiagnosticsElement()
        tmp_dump_folder = tmp_path.joinpath("tmp")
        tmp_dump_folder.mkdir(parents=True, exist_ok=True)
        filepath = next(
            diagnostics_element.add_or_get_files(omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder)
        )

        assert isinstance(filepath, Path)
        assert filepath == tmp_dump_folder.joinpath("rpm_packages.csv")

        content = filepath.open().read()

        assert "libgcc;11.4.1;2.1.el9;x86_64" in content

        shutil.rmtree(str(test_bin_dir))


def test_diagnostics_element_omd_config() -> None:
    diagnostics_element = diagnostics.OMDConfigDiagnosticsElement(omd_config={})
    assert diagnostics_element.title == "OMD Config"
    assert diagnostics_element.description == (
        "Apache mode and TCP address and port, core, "
        "Liveproxy daemon and Livestatus TCP mode, "
        "event daemon config, graphical user interface (GUI) authorization, "
        "NSCA mode, TMP file system mode"
    )
    assert diagnostics_element.filename == "omd_config.json"


def test_diagnostics_element_omd_config_content(
    tmp_path: Path,
) -> None:
    omd_config = {
        "CONFIG_ADMIN_MAIL": "",
        "CONFIG_APACHE_MODE": "own",
        "CONFIG_APACHE_TCP_ADDR": "127.0.0.1",
        "CONFIG_APACHE_TCP_PORT": "5000",
        "CONFIG_AUTOSTART": "off",
        "CONFIG_CORE": "cmc",
        "CONFIG_LIVEPROXYD": "on",
        "CONFIG_LIVESTATUS_TCP": "off",
        "CONFIG_LIVESTATUS_TCP_ONLY_FROM": "0.0.0.0 ::/0",
        "CONFIG_LIVESTATUS_TCP_PORT": "6557",
        "CONFIG_LIVESTATUS_TCP_TLS": "on",
        "CONFIG_MKEVENTD": "on",
        "CONFIG_MKEVENTD_SNMPTRAP": "off",
        "CONFIG_MKEVENTD_SYSLOG": "on",
        "CONFIG_MKEVENTD_SYSLOG_TCP": "off",
        "CONFIG_MULTISITE_AUTHORISATION": "on",
        "CONFIG_MULTISITE_COOKIE_AUTH": "on",
        "CONFIG_NSCA": "off",
        "CONFIG_NSCA_TCP_PORT": "5667",
        "CONFIG_PNP4NAGIOS": "on",
        "CONFIG_TMPFS": "on",
    }

    diagnostics_element = diagnostics.OMDConfigDiagnosticsElement(omd_config=omd_config)

    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)
    filepath = next(
        diagnostics_element.add_or_get_files(omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder)
    )

    assert isinstance(filepath, Path)
    assert filepath == tmp_dump_folder.joinpath("omd_config.json")

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
            "off",
            "5667",
            "on",
            "on",
        ],
    ):
        assert content[key] == value


@pytest.mark.parametrize(
    "host_list, raw_tree, error",
    [
        ([], None, "No Checkmk server found"),
        ([["checkmk-server-name"]], None, "No HW/SW Inventory tree of 'checkmk-server-name' found"),
        (
            [["checkmk-server-name"]],
            {
                "hardware": {},
                "networking": {},
                "software": {
                    "applications": {},
                },
            },
            "No HW/SW Inventory node 'Software > Applications > Checkmk'",
        ),
    ],
)
def test_diagnostics_element_checkmk_overview_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    _fake_local_connection: Callable,
    host_list: Sequence[Sequence[str]],
    raw_tree: SDRawTree | None,
    error: str,
) -> None:
    inv_store = InventoryStore(tmp_path)

    monkeypatch.setattr(livestatus, "LocalConnection", _fake_local_connection(host_list))

    if raw_tree:
        # Fake HW/SW Inventory tree
        inv_store.save_inventory_tree(
            host_name=HostName("checkmk-server-name"),
            tree=deserialize_tree(raw_tree),
            meta=make_meta(do_archive=False),
        )

    with pytest.raises(diagnostics.DiagnosticsElementWarning) as e:
        diagnostics._get_checkmk_overview_content(inv_store, "")
        assert error == str(e)


def test_diagnostics_element_checkmk_overview_content(tmp_path: Path) -> None:
    inv_store = InventoryStore(tmp_path)

    # Fake HW/SW Inventory tree
    inv_store.save_inventory_tree(
        host_name=HostName("checkmk-server-name"),
        tree=deserialize_tree(
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
            }
        ),
        meta=make_meta(do_archive=False),
    )

    content = json.loads(
        diagnostics._get_checkmk_overview_content(inv_store, "checkmk-server-name")
    )

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

    rows = content["Nodes"]["versions"]["Table"]["Rows"]
    assert len(rows) == 2
    for row in [
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
    ]:
        assert row in rows


@pytest.mark.parametrize(
    "diag_elem, title, description",
    [
        (
            diagnostics.CheckmkConfigFilesDiagnosticsElement,
            "Checkmk Configuration Files",
            "Configuration files ('*.mk' or '*.conf') from etc/checkmk:",
        ),
        (
            diagnostics.CheckmkLogFilesDiagnosticsElement,
            "Checkmk Log Files",
            "Log files ('*.log' or '*.state') from var/log:",
        ),
    ],
)
def test_diagnostics_element_checkmk_files(
    diag_elem: type[diagnostics.ABCCheckmkFilesDiagnosticsElement],
    title: str,
    description: str,
    tmp_path: Path,
) -> None:
    files = ["/path/to/raw-conf-file1", "/path/to/raw-conf-file2"]
    diagnostics_element = diag_elem(files)
    assert diagnostics_element.title == title
    assert diagnostics_element.description == (f"{description} {', '.join(files)}")


@pytest.mark.parametrize(
    "diag_elem",
    [
        diagnostics.CheckmkConfigFilesDiagnosticsElement,
        diagnostics.CheckmkLogFilesDiagnosticsElement,
    ],
)
def test_diagnostics_element_checkmk_files_error(
    tmp_path: Path,
    diag_elem: (
        type[diagnostics.CheckmkConfigFilesDiagnosticsElement]
        | type[diagnostics.CheckmkLogFilesDiagnosticsElement]
    ),
) -> None:
    short_test_conf_filepath = "/no/such/file"
    diagnostics_element = diag_elem([short_test_conf_filepath])
    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)

    with pytest.raises(diagnostics.DiagnosticsElementError) as e:
        next(
            diagnostics_element.add_or_get_files(
                omd_root=cmk.utils.paths.omd_root, tmp_dump_folder=tmp_dump_folder
            )
        )
        assert "No such files %s" % short_test_conf_filepath == str(e)


@pytest.mark.parametrize(
    "diag_elem, test_dir, test_filename",
    [
        (
            diagnostics.CheckmkConfigFilesDiagnosticsElement,
            cmk.utils.paths.default_config_dir,
            "test.conf",
        ),
        (
            diagnostics.CheckmkLogFilesDiagnosticsElement,
            cmk.utils.paths.log_dir,
            "test.log",
        ),
    ],
    ids=["conf", "log"],
)
def test_diagnostics_element_checkmk_files_content(
    tmp_path: Path,
    diag_elem: type[diagnostics.ABCCheckmkFilesDiagnosticsElement],
    test_dir: Path,
    test_filename: str,
) -> None:
    test_conf_dir = Path(test_dir) / "test"
    test_conf_dir.mkdir(parents=True, exist_ok=True)
    test_conf_filepath = test_conf_dir.joinpath(test_filename)
    with test_conf_filepath.open("w", encoding="utf-8") as f:
        f.write("testvar = testvalue")

    relative_path = str(Path(test_dir).relative_to(cmk.utils.paths.omd_root))
    short_test_conf_filepath = str(Path(test_conf_filepath).relative_to(test_dir))
    diagnostics_element = diag_elem([short_test_conf_filepath])
    tmp_dump_folder = tmp_path / "tmp"
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)
    filepath = next(
        diagnostics_element.add_or_get_files(
            omd_root=cmk.utils.paths.omd_root, tmp_dump_folder=tmp_dump_folder
        )
    )

    assert filepath == tmp_dump_folder.joinpath(f"{relative_path}/test/{test_filename}")

    with filepath.open("r", encoding="utf-8") as f:
        content = f.read()

    assert content == "testvar = testvalue"


@pytest.mark.parametrize(
    "host_list, status_code, text, content, warning, error",
    [
        # no Checkmk server
        ([], 123, "", b"", "No Checkmk server found", None),
        ([], 200, "<html>foo bar</html>", b"", "No Checkmk server found", None),
        ([], 200, "", b"", "No Checkmk server found", None),
        ([], 200, "", b"%PDF-", "No Checkmk server found", None),
        # Checkmk server
        ([["checkmk-server-name"]], 123, "", b"", None, "HTTP error - 123 ()"),
        (
            [["checkmk-server-name"]],
            200,
            "<html>foo bar</html>",
            b"",
            None,
            "Login failed - Invalid automation user or secret",
        ),
        (
            [["checkmk-server-name"]],
            200,
            "",
            b"",
            None,
            "Verification of PDF document header failed",
        ),
    ],
)
def test_diagnostics_element_performance_graphs_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    _fake_local_connection: Callable,
    host_list: Sequence[Sequence[str]],
    status_code: int,
    text: str,
    content: str,
    warning: str | None,
    error: str | None,
) -> None:
    omd_config = {
        "CONFIG_APACHE_TCP_ADDR": "127.0.0.1",
        "CONFIG_APACHE_TCP_PORT": "5000",
    }
    diagnostics_element = diagnostics.PerformanceGraphsDiagnosticsElement("", omd_config=omd_config)

    monkeypatch.setattr(livestatus, "LocalConnection", _fake_local_connection(host_list))

    class FakeResponse(NamedTuple):
        status_code: int
        text: str
        content: str

    monkeypatch.setattr(
        requests, "post", lambda *arg, **kwargs: FakeResponse(status_code, text, content)
    )

    automation_dir = cmk.utils.paths.var_dir / "web/automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    with automation_dir.joinpath("automation.secret").open("w") as f:
        f.write("my-123-password")

    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)

    if warning:
        with pytest.raises(diagnostics.DiagnosticsElementWarning) as w:
            next(
                diagnostics_element.add_or_get_files(
                    omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder
                )
            )
            assert warning == str(w)

    if error:
        with pytest.raises(diagnostics.DiagnosticsElementError) as e:
            next(
                diagnostics_element.add_or_get_files(
                    omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder
                )
            )
            assert error == str(e)

    shutil.rmtree(str(automation_dir))


@pytest.mark.parametrize(
    "host_list, status_code, text, content",
    [
        ([["checkmk-server-name"]], 200, "", b"%PDF-"),
    ],
)
def test_diagnostics_element_performance_graphs_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    _fake_local_connection: Callable,
    host_list: Sequence[Sequence[str]],
    status_code: int,
    text: str,
    content: str,
) -> None:
    omd_config = {
        "CONFIG_APACHE_TCP_ADDR": "127.0.0.1",
        "CONFIG_APACHE_TCP_PORT": "5000",
    }
    diagnostics_element = diagnostics.PerformanceGraphsDiagnosticsElement("", omd_config=omd_config)

    monkeypatch.setattr(livestatus, "LocalConnection", _fake_local_connection(host_list))

    class FakeResponse(NamedTuple):
        status_code: int
        text: str
        content: str

    monkeypatch.setattr(
        requests, "post", lambda *arg, **kwargs: FakeResponse(status_code, text, content)
    )

    automation_dir = cmk.utils.paths.var_dir / "web/automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    with automation_dir.joinpath("automation.secret").open("w") as f:
        f.write("my-123-password")

    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)
    filepath = next(
        diagnostics_element.add_or_get_files(omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder)
    )

    assert isinstance(filepath, Path)
    assert filepath == tmp_dump_folder.joinpath("performance_graphs.pdf")

    shutil.rmtree(str(automation_dir))


def test_diagnostics_element_se_linux() -> None:
    diagnostics_element = diagnostics.SELinuxJSONDiagnosticsElement()
    assert diagnostics_element.title == "SELinux information"
    assert diagnostics_element.description == (
        "Output of `sestatus`. See the corresponding command line help for more details."
    )
    assert diagnostics_element.filename == "selinux.json"


def test_diagnostics_element_se_linux_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    omd_root = tmp_path.joinpath("omd_root")
    test_bin_dir = Path(omd_root).joinpath("bin")
    test_bin_dir.mkdir(parents=True, exist_ok=True)
    test_bin_filepath = test_bin_dir.joinpath("sestatus")

    with test_bin_filepath.open("w", encoding="utf-8") as f:
        f.write(
            """#!/bin/bash
                echo "SELinux status:                 enabled"
                """
        )

    os.chmod(test_bin_filepath, 0o770)

    with monkeypatch.context() as m:
        m.setenv("PATH", str(test_bin_dir))

        diagnostics_element = diagnostics.SELinuxJSONDiagnosticsElement()
        tmp_dump_folder = tmp_path.joinpath("tmp")
        tmp_dump_folder.mkdir(parents=True, exist_ok=True)
        filepath = next(
            diagnostics_element.add_or_get_files(omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder)
        )

        assert isinstance(filepath, Path)
        assert filepath == tmp_dump_folder.joinpath("selinux.json")

        content = json.loads(filepath.open().read())

        assert content["SELinux status"] == "enabled"

        shutil.rmtree(str(test_bin_dir))


def test_diagnostics_element_cma() -> None:
    diagnostics_element = diagnostics.CMAJSONDiagnosticsElement()
    assert diagnostics_element.title == "Checkmk appliance information"
    assert diagnostics_element.description == (
        "Information about the appliance hardware and firmware version."
    )
    assert diagnostics_element.filename == "appliance.json"


def test_diagnostics_element_cma_content(tmp_path: Path) -> None:
    data_dict = {
        "/etc/cma/hw": "product='Checkmk rack1 Mark VI'",
        "/ro/usr/share/cma/version": "1.7.5",
    }

    def open_side_effect(name, *_args, **_kwargs):
        return mock_open(read_data=data_dict.get(name))()

    with patch("builtins.open") as bo:
        bo.side_effect = open_side_effect

        diagnostics_element = diagnostics.CMAJSONDiagnosticsElement()
        tmp_dump_folder = tmp_path.joinpath("tmp")
        tmp_dump_folder.mkdir(parents=True, exist_ok=True)
        filepath = next(
            diagnostics_element.add_or_get_files(omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder)
        )

        assert isinstance(filepath, Path)
        assert filepath == tmp_dump_folder.joinpath("appliance.json")

        content = json.loads(filepath.open().read())

        assert content["hw"]["product"] == "Checkmk rack1 Mark VI"
        assert content["fw"] == "1.7.5"


def test_diagnostics_element_crash_dumps_content(tmp_path: Path) -> None:
    omd_root = tmp_path.joinpath("omd_root")
    test_uuid = str(uuid.uuid4())
    category = "checks"
    test_crash_dir = make_crash_report_base_path(omd_root).joinpath(category).joinpath(test_uuid)
    test_crash_dir.mkdir(parents=True, exist_ok=True)
    test_crash_filepath = test_crash_dir.joinpath("info.json")
    with test_crash_filepath.open("w", encoding="utf-8") as f:
        f.write('{ "testvar": "testvalue"}')

    diagnostics_element = diagnostics.CrashDumpsDiagnosticsElement()
    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)
    filepath = next(
        diagnostics_element.add_or_get_files(omd_root=omd_root, tmp_dump_folder=tmp_dump_folder)
    )

    relative_path = make_crash_report_base_path(omd_root).relative_to(omd_root)
    test_filename = f"{test_uuid}.tar.gz"
    assert filepath == tmp_dump_folder.joinpath(relative_path).joinpath(
        f"{category}/{test_filename}"
    )

    import tarfile

    assert tarfile.is_tarfile(filepath)
    with tarfile.open(filepath, "r") as tar:
        tar.extractall(path=tmp_path, filter="data")
        with tmp_path.joinpath("info.json").open("r", encoding="utf-8") as f:
            content = f.read()

    assert json.loads(content)["testvar"] == "testvalue"
