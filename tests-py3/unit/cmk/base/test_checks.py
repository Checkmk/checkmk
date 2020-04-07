#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import re
import sys

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import

import pytest  # type: ignore[import]

import testlib  # type: ignore[import]
from testlib.base import Scenario  # type: ignore[import]

import cmk.utils.paths
import cmk.base.config as config
import cmk.base.check_utils
import cmk.base.check_api as check_api


def _search_deprecated_api_feature(check_file_path, deprecated_pattern):
    try:
        with check_file_path.open() as handle:
            return [
                "%s:%d:%s" % (check_file_path.name, line_no, repr(line.strip()))
                for line_no, line in enumerate(handle, 1)
                if re.search(deprecated_pattern, line.strip())
            ]
    except UnicodeDecodeError as exc:
        return ["%s:-1:Unable to reade file: %s" % (check_file_path.name, exc)]


@pytest.mark.parametrize("deprecated_pattern", [
    r"\bservice_description\(",
    r"\bOID_BIN\b",
    r"\bOID_STRING\b",
    r"\bOID_END_BIN\b",
    r"\bOID_END_OCTET_STRING\b",
    r"\ball_matching_hosts\b",
    r"\bbinstring_to_int\b",
    r"\bcheck_type\b",
    r"\bcore_state_names\b",
    r"\bget_http_proxy\b",
    r"\bhosttags_match_taglist\b",
    r"\bin_extraconf_hostlist\b",
    r"\bis_cmc\b",
    r"\bnagios_illegal_chars\b",
    r"\bquote_shell_string\b",
    r"\btags_of_host\b",
])
def test_deprecated_api_features(deprecated_pattern):
    check_files = Path(cmk.utils.paths.checks_dir).glob("*")
    check_files = (p for p in check_files if p.suffix not in (".swp",))
    with_deprecated_feature = [
        finding  #
        for check_file_path in check_files  #
        for finding in _search_deprecated_api_feature(check_file_path, deprecated_pattern)
    ]
    assert not with_deprecated_feature, "Found %d deprecated API name '%r' usages:\n%s" % (
        len(with_deprecated_feature),
        deprecated_pattern,
        "\n".join(with_deprecated_feature),
    )


def _search_from_imports(check_file_path):
    with open(check_file_path) as f_:
        return [
            "%s:%d:%s" % (Path(check_file_path).stem, line_no, repr(line.strip()))
            for line_no, line in enumerate(f_.readlines(), 1)
            if re.search(r'from\s.*\simport\s', line.strip())
        ]


def test_imports_in_checks():
    check_files = config.get_plugin_paths(cmk.utils.paths.checks_dir)
    with_from_imports = [
        finding  #
        for check_file_path in check_files  #
        for finding in _search_from_imports(check_file_path)
    ]
    assert not with_from_imports, "Found %d from-imports:\n%s" % (len(with_from_imports),
                                                                  "\n".join(with_from_imports))


def test_load_checks():
    config._initialize_data_structures()
    assert config.check_info == {}
    config.load_all_checks(check_api.get_check_api_context)
    assert len(config.check_info) > 1000


def test_is_tcp_check():
    config.load_all_checks(check_api.get_check_api_context)
    assert cmk.base.check_utils.is_tcp_check("xxx") is False
    assert cmk.base.check_utils.is_tcp_check("uptime") is True
    assert cmk.base.check_utils.is_tcp_check("uptime") is True
    assert cmk.base.check_utils.is_tcp_check("snmp_uptime") is False
    assert cmk.base.check_utils.is_tcp_check("mem") is True
    assert cmk.base.check_utils.is_tcp_check("mem.linux") is True
    assert cmk.base.check_utils.is_tcp_check("mem.ding") is True
    assert cmk.base.check_utils.is_tcp_check("apc_humidity") is False


def test_is_snmp_check():
    config.load_all_checks(check_api.get_check_api_context)
    assert cmk.base.check_utils.is_snmp_check("xxx") is False
    assert cmk.base.check_utils.is_snmp_check("uptime") is False
    assert cmk.base.check_utils.is_snmp_check("uptime") is False
    assert cmk.base.check_utils.is_snmp_check("snmp_uptime") is True
    assert cmk.base.check_utils.is_snmp_check("mem") is False
    assert cmk.base.check_utils.is_snmp_check("mem.linux") is False
    assert cmk.base.check_utils.is_snmp_check("mem.ding") is False
    assert cmk.base.check_utils.is_snmp_check("apc_humidity") is True
    assert cmk.base.check_utils.is_snmp_check("brocade.power") is True
    assert cmk.base.check_utils.is_snmp_check("brocade.fan") is True
    assert cmk.base.check_utils.is_snmp_check("brocade.xy") is True
    assert cmk.base.check_utils.is_snmp_check("brocade") is True


def test_discoverable_tcp_checks():
    config.load_all_checks(check_api.get_check_api_context)
    assert "uptime" in config.discoverable_tcp_checks()
    assert "snmp_uptime" not in config.discoverable_tcp_checks()
    assert "logwatch" in config.discoverable_tcp_checks()


# ########### Management board checks


def _check_plugins():
    return {
        "tcp_check_mgmt_only": "mgmt_only",
        "tcp_check_host_precedence": "host_precedence",
        "tcp_check_host_only": "host_only",
        "snmp_check_mgmt_only": "mgmt_only",
        "snmp_check_host_precedence": "host_precedence",
        "snmp_check_host_only": "host_only",
    }


@pytest.fixture()
def patch_mgmt_board_plugins(monkeypatch):
    monkeypatch.setattr(config, "_get_management_board_precedence",
                        lambda c, _: _check_plugins()[c])
    monkeypatch.setattr(cmk.base.check_utils, "is_snmp_check", lambda c: c.startswith("snmp_"))


# ########### Unknown check plugins


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,result", [
    (False, []),
    (True, []),
])
def test_filter_by_management_board_unknown_check_plugins(monkeypatch, for_discovery, result):
    ts = Scenario()
    ts.add_host("this_host")
    ts.apply(monkeypatch)

    found_check_plugins = set(_check_plugins())
    monkeypatch.setattr(config, "check_info", [])

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(result)


# ########### TCP host


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,result", [
    (False, ["tcp_check_host_precedence", "tcp_check_host_only"]),
    (True, ["tcp_check_host_precedence", "tcp_check_host_only"]),
])
def test_filter_by_management_board_TCP_host_without_mgmt_board(monkeypatch, for_discovery, result):
    ts = Scenario()
    ts.add_host("this_host")
    ts.apply(monkeypatch)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("tcp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(result)


# ########### SNMP host


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,result", [
    (False, ["snmp_check_host_precedence", "snmp_check_host_only"]),
    (True, ["snmp_check_host_precedence", "snmp_check_host_only"]),
])
def test_filter_by_management_board_SNMP_host_without_mgmt_board(monkeypatch, for_discovery,
                                                                 result):
    ts = Scenario()
    ts.add_host("this_host", tags={"snmp_ds": "snmp-v1", "agent": "no-agent"})
    ts.apply(monkeypatch)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(result)


# ########### Dual host


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,result", [
    (False, [
        "tcp_check_host_precedence", "tcp_check_host_only", "snmp_check_host_precedence",
        "snmp_check_host_only"
    ]),
    (True, [
        "tcp_check_host_precedence", "tcp_check_host_only", "snmp_check_host_precedence",
        "snmp_check_host_only"
    ]),
])
def test_filter_by_management_board_dual_host_without_mgmt_board(monkeypatch, for_discovery,
                                                                 result):
    ts = Scenario()
    ts.add_host("this_host", tags={"snmp_ds": "snmp-v1", "agent": "cmk-agent"})
    ts.apply(monkeypatch)

    found_check_plugins = set(_check_plugins())
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(result)


# ########### TCP host + SNMP Management Board


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,host_result,mgmt_board_result", [
    (False, ["tcp_check_host_precedence", "tcp_check_host_only"
            ], ["snmp_check_mgmt_only", "snmp_check_host_precedence", "snmp_check_host_only"]),
    (True, ["tcp_check_host_precedence", "tcp_check_host_only"
           ], ["snmp_check_mgmt_only", "snmp_check_host_precedence"]),
])
def test_filter_by_management_board_TCP_host_with_SNMP_mgmt_board(monkeypatch, for_discovery,
                                                                  host_result, mgmt_board_result):
    ts = Scenario()
    ts.add_host("this_host", tags={
        "agent": "cmk-agent",
    })
    config_cache = ts.apply(monkeypatch)
    h = config_cache.get_host_config("this_host")
    h.has_management_board = True

    found_check_plugins = [c for c in _check_plugins() if c.startswith("tcp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(host_result)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             True,
                                             for_discovery=for_discovery) == set(mgmt_board_result)


# ########### SNMP host + SNMP Management Board


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,host_result,mgmt_board_result", [
    (False, ["snmp_check_host_only", "snmp_check_host_precedence"], ["snmp_check_mgmt_only"]),
    (True, ["snmp_check_host_only", "snmp_check_host_precedence"], ["snmp_check_mgmt_only"]),
])
def test_filter_by_management_board_SNMP_host_with_SNMP_mgmt_board(monkeypatch, for_discovery,
                                                                   host_result, mgmt_board_result):
    ts = Scenario()
    ts.add_host("this_host", tags={"snmp_ds": "snmp-v1", "agent": "no-agent"})
    config_cache = ts.apply(monkeypatch)
    h = config_cache.get_host_config("this_host")
    h.has_management_board = True

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(host_result)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             True,
                                             for_discovery=for_discovery) == set(mgmt_board_result)


# ########### Dual host + SNMP Management Board


@pytest.mark.usefixtures("patch_mgmt_board_plugins")
@pytest.mark.parametrize("for_discovery,host_result,mgmt_board_result", [
    (False, [
        "tcp_check_host_precedence", "tcp_check_host_only", "snmp_check_host_only",
        "snmp_check_host_precedence"
    ], ["snmp_check_mgmt_only"]),
    (True, [
        "tcp_check_host_precedence", "tcp_check_host_only", "snmp_check_host_only",
        "snmp_check_host_precedence"
    ], ["snmp_check_mgmt_only"]),
])
def test_filter_by_management_board_dual_host_with_SNMP_mgmt_board(monkeypatch, for_discovery,
                                                                   host_result, mgmt_board_result):
    ts = Scenario()
    ts.add_host("this_host", tags={"snmp_ds": "snmp-v1", "agent": "cmk-agent"})
    config_cache = ts.apply(monkeypatch)
    h = config_cache.get_host_config("this_host")
    h.has_management_board = True

    found_check_plugins = set(_check_plugins())
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             False,
                                             for_discovery=for_discovery) == set(host_result)

    found_check_plugins = [c for c in _check_plugins() if c.startswith("snmp_")]
    monkeypatch.setattr(config, "check_info", found_check_plugins)

    assert config.filter_by_management_board("this_host",
                                             found_check_plugins,
                                             True,
                                             for_discovery=for_discovery) == set(mgmt_board_result)


def test_py2_check_tests():
    check_tests = Path(testlib.repo_path()).joinpath(Path('tests/unit/checks'))
    generic_check_tests = Path(testlib.repo_path()).joinpath(
        Path('tests/unit/checks/generictests/datasets'))

    if check_tests.exists():
        py2_check_tests = set(p.name for p in check_tests.glob('test_*.py'))
        assert py2_check_tests == set(
        ), "Found deprecated Python 2 check tests: %s" % ", ".join(py2_check_tests)

    if generic_check_tests.exists():
        py2_generic_check_tests = set(p.name for p in generic_check_tests.glob('*.py'))
        assert py2_generic_check_tests == set(
        ), "Found deprecated Python 2 generic check tests: %s" % ", ".join(py2_generic_check_tests)


def test_check_plugin_header():
    for checkfile in Path(testlib.repo_path()).joinpath(Path('checks')).iterdir():
        if checkfile.name.startswith("."):
            # .f12
            continue
        with checkfile.open() as f:
            shebang = f.readline().strip()
            encoding_header = f.readline().strip()

        assert shebang == "#!/usr/bin/env python3", "Check plugin '%s' has wrong shebang '%s'" % (
            checkfile.name, shebang)
        assert encoding_header == "# -*- coding: utf-8 -*-", "Check plugin '%s' has wrong encoding header '%s'" % (
            checkfile.name, encoding_header)


def test_py2_inv_plugins_tests():
    inv_plugin_tests = Path(testlib.repo_path()).joinpath(Path('tests/unit/inventory'))
    py2_inv_plugin_tests = set(p.name for p in inv_plugin_tests.glob('test_*.py'))

    if inv_plugin_tests.exists():
        assert py2_inv_plugin_tests == set(
        ), "Found deprecated Python 2 inventory plugin tests: %s" % ", ".join(py2_inv_plugin_tests)


def test_inventory_plugin_header():
    for inventory_pluginfile in Path(testlib.repo_path()).joinpath(Path('inventory')).iterdir():
        if inventory_pluginfile.name.startswith("."):
            # .f12
            continue
        with inventory_pluginfile.open() as f:
            shebang = f.readline().strip()
            encoding_header = f.readline().strip()
        assert shebang == "#!/usr/bin/env python3", "Inventory plugin '%s' has wrong shebang '%s'" % (
            inventory_pluginfile.name, shebang)
        assert encoding_header == "# -*- coding: utf-8 -*-", "Inventory plugin '%s' has wrong encoding header '%s'" % (
            inventory_pluginfile.name, encoding_header)
