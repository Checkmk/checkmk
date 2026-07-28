#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import csv
import io
import json
import os
from pathlib import Path, PurePosixPath
from unittest.mock import mock_open, patch

import pytest

from cmk.diagnostics.internal import CollectContext, CollectInfo, GeneratedContent
from cmk.plugins.diagnostics.diagnostics.operating_system import (
    _collect_hw_info,
    _collect_vendor_info,
    diagnostics_plugin_appliance_info,
    diagnostics_plugin_disk_usage,
    diagnostics_plugin_environment_variables,
    diagnostics_plugin_file_sizes,
    diagnostics_plugin_os_packages,
    diagnostics_plugin_selinux,
)


def _make_context(tmp_path: Path) -> CollectContext:
    return CollectContext(
        omd_root=tmp_path,
        omd_config={},
        all_parameters={},
        base_config={},
        resolve_checkmk_server_host=lambda: "checkmk_server",
        site_internal_auth_header=lambda: "InternalToken deadbeef",
        log=None,  # type: ignore[arg-type]  # not used
    )


def _make_fake_binary(bin_dir: Path, name: str, script: str) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    binary = bin_dir / name
    binary.write_text(script)
    os.chmod(binary, 0o770)


def test_environment_variables_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    environment_vars = {"France": "Paris", "Italy": "Rome", "Germany": "Berlin"}
    with monkeypatch.context() as m:
        for key, value in environment_vars.items():
            m.setenv(key, value)

        items = list(diagnostics_plugin_environment_variables.handler(_make_context(tmp_path)))

    assert len(items) == 1
    arcname, content = items[0].path, items[0].content
    assert arcname == PurePosixPath("environment.json")
    assert isinstance(content, GeneratedContent)
    parsed = json.loads(content.data)
    for key, value in environment_vars.items():
        assert parsed[key] == value


def test_hw_info_content(tmp_path: Path) -> None:
    proc_path = tmp_path.joinpath("proc")
    proc_path.mkdir(exist_ok=True)

    # Create three fake proc files
    (proc_path / "meminfo").write_text("MemTotal:       32663516 kB")
    (proc_path / "loadavg").write_text("1.19 1.58 1.75 2/1922 891074")
    (proc_path / "cpuinfo").write_text("""processor : 0
physical id : 0
processor   : 1
physical id : 0
processor   : 2
physical id : 0
processor   : 3
physical id : 0""")

    items = list(_collect_hw_info(_make_context(tmp_path), proc_path=proc_path))

    assert len(items) == 1
    arcname, content = items[0].path, items[0].content
    assert arcname == PurePosixPath("hwinfo.json")
    assert isinstance(content, GeneratedContent)
    assert json.loads(content.data) == {
        "meminfo": {"MemTotal": "32663516 kB"},
        "loadavg": {"loadavg_1": "1.19", "loadavg_5": "1.58", "loadavg_15": "1.75"},
        "cpuinfo": {"physical_id": "0", "num_logical_processors": "4", "cpus": 1},
    }


def test_vendor_info_content(tmp_path: Path) -> None:
    dmi_id_path = tmp_path.joinpath("sys/class/dmi/id")
    dmi_id_path.mkdir(parents=True, exist_ok=True)

    # Create five fake sys files
    (dmi_id_path / "bios_vendor").write_text("Dull Ink")
    (dmi_id_path / "bios_version").write_text("1.2.3")
    (dmi_id_path / "sys_vendor").write_text("Dull Ink")
    (dmi_id_path / "product_name").write_text("Longitude 4")
    (dmi_id_path / "chassis_asset_tag").write_text("")

    items = list(_collect_vendor_info(_make_context(tmp_path), dmi_id_path=dmi_id_path))

    assert len(items) == 1
    arcname, content = items[0].path, items[0].content
    assert arcname == PurePosixPath("vendorinfo.json")
    assert isinstance(content, GeneratedContent)
    assert json.loads(content.data) == {
        "bios_vendor": "Dull Ink",
        "bios_version": "1.2.3",
        "chassis_asset_tag": "Other",
        "product_name": "Longitude 4",
        "sys_vendor": "Dull Ink",
    }


def test_appliance_info_content(tmp_path: Path) -> None:
    data_dict = {
        "/etc/cma/hw": "product='Checkmk rack1 Mark VI'",
        "/ro/usr/share/cma/version": "1.7.5",
    }

    def open_side_effect(name: object, *_args: object, **_kwargs: object) -> object:
        return mock_open(read_data=data_dict.get(str(name)))()

    with patch("builtins.open") as bo:
        bo.side_effect = open_side_effect

        items = list(diagnostics_plugin_appliance_info.handler(_make_context(tmp_path)))

    assert len(items) == 1
    arcname, content = items[0].path, items[0].content
    assert arcname == PurePosixPath("appliance.json")
    assert isinstance(content, GeneratedContent)
    parsed = json.loads(content.data)
    assert parsed["hw"]["product"] == "Checkmk rack1 Mark VI"
    assert parsed["fw"] == "1.7.5"


def test_selinux_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_bin_dir = tmp_path.joinpath("bin")
    _make_fake_binary(
        test_bin_dir,
        "sestatus",
        """#!/bin/bash
            echo "SELinux status:                 enabled"
            """,
    )

    with monkeypatch.context() as m:
        m.setenv("PATH", str(test_bin_dir))

        items = list(diagnostics_plugin_selinux.handler(_make_context(tmp_path)))

    assert len(items) == 1
    arcname, content = items[0].path, items[0].content
    assert arcname == PurePosixPath("selinux.json")
    assert isinstance(content, GeneratedContent)
    assert json.loads(content.data)["SELinux status"] == "enabled"


def test_os_packages_dpkg_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_bin_dir = tmp_path.joinpath("bin")
    _make_fake_binary(
        test_bin_dir,
        "dpkg",
        """#!/bin/bash
            echo "Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name                                                        Version                                         Architecture Description
+++-===========================================================-===============================================-============-=====================================================================================================
ii  accountsservice                                             22.07.5-2ubuntu1.5                              amd64        query and manipulate user account information"
            """,
    )

    with monkeypatch.context() as m:
        m.setenv("PATH", str(test_bin_dir))

        items = {
            i.path: i.content
            for i in diagnostics_plugin_os_packages.handler(_make_context(tmp_path))
        }

    # rpm is not available on the fake PATH, so only the dpkg file is packed
    assert set(items) == {PurePosixPath("dpkg_packages.csv")}
    content = items[PurePosixPath("dpkg_packages.csv")]
    assert isinstance(content, GeneratedContent)
    assert b"22.07.5-2ubuntu1.5" in content.data


def test_os_packages_rpm_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_bin_dir = tmp_path.joinpath("bin")
    _make_fake_binary(
        test_bin_dir,
        "rpm",
        """#!/bin/bash
            echo "libgcc;11.4.1;2.1.el9;x86_64
crypto-policies;20230731;1.git94f0e2c.el9_3.1;noarch
tzdata;2023c;1.el9;noarch"
            """,
    )

    with monkeypatch.context() as m:
        m.setenv("PATH", str(test_bin_dir))

        items = {
            i.path: i.content
            for i in diagnostics_plugin_os_packages.handler(_make_context(tmp_path))
        }

    assert set(items) == {PurePosixPath("rpm_packages.csv")}
    content = items[PurePosixPath("rpm_packages.csv")]
    assert isinstance(content, GeneratedContent)
    assert b"libgcc;11.4.1;2.1.el9;x86_64" in content.data


def test_os_packages_no_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    empty_bin_dir = tmp_path.joinpath("bin")
    empty_bin_dir.mkdir(parents=True, exist_ok=True)

    with monkeypatch.context() as m:
        m.setenv("PATH", str(empty_bin_dir))

        with pytest.raises(CollectInfo, match="No data"):
            list(diagnostics_plugin_os_packages.handler(_make_context(tmp_path)))


def test_disk_usage_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    test_bin_dir = tmp_path.joinpath("bin")
    _make_fake_binary(
        test_bin_dir,
        "df",
        """#!/bin/bash
            echo "Filesystem 1K-blocks Used Available Use% Mounted on"
            """,
    )

    with monkeypatch.context() as m:
        m.setenv("PATH", str(test_bin_dir))

        items = {
            i.path: i.content
            for i in diagnostics_plugin_disk_usage.handler(_make_context(tmp_path))
        }

    assert set(items) == {PurePosixPath("command_df.out"), PurePosixPath("command_df-i.out")}
    content = items[PurePosixPath("command_df.out")]
    assert isinstance(content, GeneratedContent)
    assert b"Filesystem" in content.data


def test_disk_usage_command_not_available(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    empty_bin_dir = tmp_path.joinpath("bin")
    empty_bin_dir.mkdir(parents=True, exist_ok=True)

    with monkeypatch.context() as m:
        m.setenv("PATH", str(empty_bin_dir))

        with pytest.raises(CollectInfo, match="Command df not available on this system."):
            list(diagnostics_plugin_disk_usage.handler(_make_context(tmp_path)))


def _file_sizes_rows(tmp_path: Path) -> list[dict[str, str]]:
    items = {
        i.path: i.content for i in diagnostics_plugin_file_sizes.handler(_make_context(tmp_path))
    }
    content = items[PurePosixPath("file_size.csv")]
    assert isinstance(content, GeneratedContent)
    reader = csv.DictReader(io.StringIO(content.data.decode()), delimiter=";", quotechar="'")
    return list(reader)


def test_file_sizes_content(tmp_path: Path) -> None:
    test_dir = tmp_path / "local/share/check_mk/checks"
    test_dir.mkdir(parents=True)
    test_file = test_dir / "testfile"
    test_content = "test\n"
    test_file.write_text(test_content)

    with patch("pathlib.Path.group", return_value="dummygroup"):
        rows = _file_sizes_rows(tmp_path)

    by_path = {row["path"]: row for row in rows}
    assert str(test_file) in by_path
    assert by_path[str(test_file)]["size"] == str(len(test_content))
    assert by_path[str(test_file)]["group"] == "dummygroup"
    assert sorted(rows[-1].keys()) == sorted(["path", "size", "owner", "group", "mode", "changed"])


def test_file_sizes_ignores_temporary_files(tmp_path: Path) -> None:
    test_dir = tmp_path / "local/share/check_mk/checks"
    test_dir.mkdir(parents=True)
    (test_dir / "testfile").write_text("test\n")
    (test_dir / ".session_info.mk.newodhsmg3r").write_text("test\n")

    with patch("pathlib.Path.group", return_value="dummygroup"):
        rows = _file_sizes_rows(tmp_path)

    assert [Path(row["path"]).name for row in rows] == ["testfile"]
