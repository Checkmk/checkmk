#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path
import shutil
import collections
import requests
import pytest  # type: ignore[import]

import livestatus

import cmk.utils.paths
import cmk.utils.packaging as packaging

import cmk.base.diagnostics as diagnostics

#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def test_diagnostics_dump_elements():
    fixed_element_classes = set([
        diagnostics.GeneralDiagnosticsElement,
    ])
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


#.
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
    assert diagnostics_element.description == ("OS, Checkmk version and edition, Time, Core, "
                                               "Python version and paths, Architecture")


def test_diagnostics_element_general_content(tmp_path):
    diagnostics_element = diagnostics.GeneralDiagnosticsElement()
    tmppath = Path(tmp_path).joinpath("tmp")
    filepath = diagnostics_element.add_or_get_file(tmppath)

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("general.json")

    info_keys = [
        "time",
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
        "This also includes information about installed MKPs.")


def test_diagnostics_element_local_files_content(tmp_path):
    diagnostics_element = diagnostics.LocalFilesDiagnosticsElement()

    def create_test_package(name):
        check_dir = cmk.utils.paths.local_checks_dir
        check_dir.mkdir(parents=True, exist_ok=True)

        with check_dir.joinpath(name).open("w", encoding="utf-8") as f:
            f.write(u"test-check\n")

        package_info = packaging.get_initial_package_info(name)
        package_info["files"] = {
            "checks": [name],
        }

        packaging.create_package(package_info)

    packaging.package_dir().mkdir(parents=True, exist_ok=True)
    name = "test-package"
    create_test_package(name)

    tmppath = Path(tmp_path).joinpath("tmp")
    filepath = diagnostics_element.add_or_get_file(tmppath)

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("local_files.json")

    info_keys = [
        "installed",
        "unpackaged",
        "parts",
        "optional_packages",
    ]
    content = json.loads(filepath.open().read())

    assert sorted(content.keys()) == sorted(info_keys)

    installed_keys = [name]
    assert sorted(content['installed'].keys()) == sorted(installed_keys)
    assert content["installed"][name]['files'] == {'checks': [name]}

    unpackaged_keys = [
        'agent_based',
        'agents',
        'alert_handlers',
        'bin',
        'checkman',
        'checks',
        'doc',
        'ec_rule_packs',
        'inventory',
        'lib',
        'locales',
        'mibs',
        'notifications',
        'pnp-templates',
        'web',
    ]
    assert sorted(content["unpackaged"].keys()) == sorted(unpackaged_keys)
    for key in unpackaged_keys:
        assert content["unpackaged"][key] == []

    parts_keys = [
        'agent_based',
        'agents',
        'alert_handlers',
        'bin',
        'checkman',
        'checks',
        'doc',
        'ec_rule_packs',
        'inventory',
        'lib',
        'locales',
        'mibs',
        'notifications',
        'pnp-templates',
        'web',
    ]
    assert sorted(content["parts"].keys()) == sorted(parts_keys)
    part_keys = [
        'files',
        'path',
        'permissions',
        'title',
    ]
    for key in parts_keys:
        assert sorted(content["parts"][key].keys()) == sorted(part_keys)
        if key == "checks":
            assert content["parts"][key]['files'] == [name]
            assert content["parts"][key]['permissions'] == [420]
        else:
            assert content["parts"][key]['files'] == []
            assert content["parts"][key]['permissions'] == []

    assert content["optional_packages"] == {}

    shutil.rmtree(str(packaging.package_dir()))


def test_diagnostics_element_omd_config():
    diagnostics_element = diagnostics.OMDConfigDiagnosticsElement()
    assert diagnostics_element.ident == "omd_config"
    assert diagnostics_element.title == "OMD Config"
    assert diagnostics_element.description == ("Apache mode and TCP address and port, Core, "
                                               "Liveproxy daemon and livestatus TCP mode, "
                                               "Event daemon config, Multiste authorisation, "
                                               "NSCA mode, TMP filesystem mode")


def test_diagnostics_element_omd_config_content(tmp_path):
    diagnostics_element = diagnostics.OMDConfigDiagnosticsElement()
    # Fake raw output of site.conf
    etc_omd_dir = Path(cmk.utils.paths.omd_root) / "etc" / "omd"
    etc_omd_dir.mkdir(parents=True, exist_ok=True)
    with etc_omd_dir.joinpath("site.conf").open("w") as f:
        f.write("""CONFIG_ADMIN_MAIL=''
CONFIG_APACHE_MODE='own'
CONFIG_APACHE_TCP_ADDR='127.0.0.1'
CONFIG_APACHE_TCP_PORT='5000'
CONFIG_AUTOSTART='off'
CONFIG_CORE='cmc'
CONFIG_DOKUWIKI_AUTH='off'
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
CONFIG_TMPFS='on'""")

    tmppath = Path(tmp_path).joinpath("tmp")
    filepath = diagnostics_element.add_or_get_file(tmppath)

    assert isinstance(filepath, Path)
    assert filepath == tmppath.joinpath("omd_config.json")

    info_keys = [
        'CONFIG_ADMIN_MAIL',
        'CONFIG_APACHE_MODE',
        'CONFIG_APACHE_TCP_ADDR',
        'CONFIG_APACHE_TCP_PORT',
        'CONFIG_AUTOSTART',
        'CONFIG_CORE',
        'CONFIG_DOKUWIKI_AUTH',
        'CONFIG_LIVEPROXYD',
        'CONFIG_LIVESTATUS_TCP',
        'CONFIG_LIVESTATUS_TCP_ONLY_FROM',
        'CONFIG_LIVESTATUS_TCP_PORT',
        'CONFIG_LIVESTATUS_TCP_TLS',
        'CONFIG_MKEVENTD',
        'CONFIG_MKEVENTD_SNMPTRAP',
        'CONFIG_MKEVENTD_SYSLOG',
        'CONFIG_MKEVENTD_SYSLOG_TCP',
        'CONFIG_MULTISITE_AUTHORISATION',
        'CONFIG_MULTISITE_COOKIE_AUTH',
        'CONFIG_NAGIOS_THEME',
        'CONFIG_NSCA',
        'CONFIG_NSCA_TCP_PORT',
        'CONFIG_PNP4NAGIOS',
        'CONFIG_TMPFS',
    ]
    content = json.loads(filepath.open().read())

    assert sorted(content.keys()) == sorted(info_keys)
    for key, value in zip(info_keys, [
            '',
            'own',
            '127.0.0.1',
            '5000',
            'off',
            'cmc',
            'off',
            'on',
            'off',
            '0.0.0.0 ::/0',
            '6557',
            'on',
            'on',
            'off',
            'on',
            'off',
            'on',
            'on',
            'classicui',
            'off',
            '5667',
            'on',
            'on',
    ]):
        assert content[key] == value

    shutil.rmtree(str(etc_omd_dir))


def test_diagnostics_element_performance_graphs():
    diagnostics_element = diagnostics.PerformanceGraphsDiagnosticsElement()
    assert diagnostics_element.ident == "performance_graphs"
    assert diagnostics_element.title == "Performance Graphs of Checkmk Server"
    assert diagnostics_element.description == (
        "CPU load and utilization, Number of threads, Kernel Performance, "
        "OMD, Filesystem, Apache Status, TCP Connections of the time ranges "
        "25 hours and 35 days")


@pytest.mark.parametrize(
    "host_attrs, status_code, text, content, error, filepath_result",
    [
        # no Checkmk server
        ({}, 123, "", b"", "HTTP error - 123 ()", False),
        ({}, 200, "<html>foo bar</html>", b"", "Login failed - Invalid automation user or secret",
         False),
        ({}, 200, "", b"", "Verification of PDF document header failed", False),
        # Checkmk server
        ({
            'cmk/check_mk_server': 'yes'
        }, 123, "", b"", "HTTP error - 123 ()", False),
        ({
            'cmk/check_mk_server': 'yes'
        }, 200, "<html>foo bar</html>", b"", "Login failed - Invalid automation user or secret",
         False),
        ({
            'cmk/check_mk_server': 'yes'
        }, 200, "", b"", "Verification of PDF document header failed", False),
        ({
            'cmk/check_mk_server': 'yes'
        }, 200, "", b"%PDF-", "", True),
    ])
def test_diagnostics_element_performance_graphs_content(monkeypatch, tmp_path, host_attrs,
                                                        status_code, text, content, error,
                                                        filepath_result):
    diagnostics_element = diagnostics.PerformanceGraphsDiagnosticsElement()

    class FakeLocalConnection:
        def query(self, query):
            return [["host-name", host_attrs]]

    monkeypatch.setattr(livestatus, "LocalConnection", FakeLocalConnection)

    FakeResponse = collections.namedtuple("FakeResponse", ["status_code", "text", "content"])
    monkeypatch.setattr(requests, "post",
                        lambda *arg, **kwargs: FakeResponse(status_code, text, content))

    automation_dir = Path(cmk.utils.paths.var_dir) / "web" / "automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    with automation_dir.joinpath("automation.secret").open("w") as f:
        f.write("my-123-password")

    etc_omd_dir = Path(cmk.utils.paths.omd_root) / "etc" / "omd"
    etc_omd_dir.mkdir(parents=True, exist_ok=True)
    with etc_omd_dir.joinpath("site.conf").open("w") as f:
        f.write("""CONFIG_APACHE_TCP_ADDR='127.0.0.1'
CONFIG_APACHE_TCP_PORT='5000'""")

    tmppath = Path(tmp_path).joinpath("tmp")
    tmppath.mkdir(parents=True, exist_ok=True)
    filepath = diagnostics_element.add_or_get_file(tmppath)

    if filepath_result:
        assert isinstance(filepath, Path)
        assert filepath == tmppath.joinpath("performance_graphs.pdf")
    else:
        assert filepath is None
    assert diagnostics_element.error == error

    shutil.rmtree(str(automation_dir))
    shutil.rmtree(str(etc_omd_dir))
