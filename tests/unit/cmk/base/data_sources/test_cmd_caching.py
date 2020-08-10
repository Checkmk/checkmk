#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# These tests verify the behaviour of the Check_MK base methods
# that do the actual checking/discovery/inventory work. Especially
# the default caching and handling of global options affecting the
# caching is checked

from functools import partial
from pathlib import Path
from typing import cast

import pytest  # type: ignore[import]

from testlib import InventoryPluginManager  # , CheckManager
from testlib.base import Scenario
from testlib.debug_utils import cmk_debug_enabled
from testlib.utils import get_standard_linux_agent_output

import cmk.utils.paths
from cmk.utils.log import logger

import cmk.base.automations
import cmk.base.automations.check_mk
import cmk.base.check_api as check_api
import cmk.base.config as config
import cmk.base.inventory_plugins
import cmk.base.modes
import cmk.base.modes.check_mk
from cmk.base.data_sources import ABCDataSource
from cmk.base.data_sources.agent import AgentDataSource
from cmk.base.data_sources.snmp import SNMPConfigurator, SNMPDataSource

# TODO: These tests need to be tuned, because they involve a lot of checks being loaded which takes
# too much time.

# TODO (mo): now it's worse, we need to load all checks. remove this with CMK-4295
#            after removing this, bring back the commented line below.


# Load some common checks to have at least some for the test execution
# Modes that have needs_checks=True set would miss the checks
# without this fixtures
@pytest.fixture(scope="module", autouse=True)
def load_plugins():
    #     CheckManager().load(["df", "cpu", "chrony", "lnx_if", "livestatus_status", "omd_status"])
    config.load_all_checks(check_api.get_check_api_context)
    InventoryPluginManager().load()


@pytest.fixture(name="scenario")
def scenario_fixture(monkeypatch):
    test_hosts = ["ds-test-host1", "ds-test-host2", "ds-test-node1", "ds-test-node2"]

    ts = Scenario()

    for h in test_hosts:
        ts.add_host(h)

    ts.set_option("ipaddresses", dict((h, "127.0.0.1") for h in test_hosts))
    ts.add_cluster("ds-test-cluster1", nodes=["ds-test-node1", "ds-test-node2"])

    ts.set_ruleset(
        "datasource_programs",
        [
            ("cat %s/<HOST>" % cmk.utils.paths.tcp_cache_dir, [], test_hosts, {}),
        ],
    )

    linux_agent_output = get_standard_linux_agent_output()

    for h in test_hosts:
        cache_path = Path(cmk.utils.paths.tcp_cache_dir, h)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        with cache_path.open("w", encoding="utf-8") as f:
            f.write(linux_agent_output)

    return ts.apply(monkeypatch)


@pytest.fixture
def reset_log_level():
    level = logger.getEffectiveLevel()
    yield
    logger.setLevel(level)


def _patch_data_source_run(mocker, **kwargs):
    defaults = {
        "_may_use_cache_file": False,
        "_use_outdated_cache_file": False,
        "_max_cachefile_age": 0,  # check_max_cachefile_age
        "_no_cache": False,
        "_use_outdated_persisted_sections": False,
        "do_snmp_scan": False,
        "on_error": "raise",
        "_use_snmpwalk_cache": True,
        "_ignore_check_interval": True,
    }
    defaults.update(kwargs)

    def _run(self, *args, callback, **kwargs):
        assert self._may_use_cache_file == defaults["_may_use_cache_file"]
        assert self._no_cache == defaults["_no_cache"]
        assert self._max_cachefile_age == defaults["_max_cachefile_age"]
        assert self._use_outdated_cache_file == defaults["_use_outdated_cache_file"]

        if isinstance(self, AgentDataSource):
            assert (self._use_outdated_persisted_sections ==
                    defaults["_use_outdated_persisted_sections"])

        elif isinstance(self, SNMPDataSource):
            configurator = cast(SNMPConfigurator, self.configurator)
            assert configurator.do_snmp_scan == defaults["do_snmp_scan"]
            assert configurator.on_snmp_scan_error == defaults["on_error"]
            assert configurator.use_snmpwalk_cache == defaults["_use_snmpwalk_cache"]
            assert configurator.ignore_check_interval == defaults["_ignore_check_interval"]

        return callback(self, *args, **kwargs)

    mocker.patch.object(
        ABCDataSource,
        "_run",
        autospec=True,
        side_effect=partial(_run, callback=ABCDataSource._run),
    )


@pytest.fixture
def patch_data_source_run(mocker):
    _patch_data_source_run(mocker)


# When called without hosts, it uses all hosts and defaults to using the data source cache
# When called with an explicit list of hosts the cache is not used by default, the option
# --cache enables it and --no-cache enforce never to use it
@pytest.mark.parametrize(
    ("hosts"),
    [
        (
            ["ds-test-host1"],
            {
                "_max_cachefile_age": 0
            },
        ),
        (
            ["ds-test-cluster1"],
            {
                "_max_cachefile_age": 90
            },
        ),
        ([], {}),
    ],
)
@pytest.mark.parametrize(
    ("cache"),
    [
        (None, {}),
        (True, {
            "_may_use_cache_file": True,
            "_use_outdated_cache_file": True
        }),
        (False, {
            "_may_use_cache_file": False,
            "_no_cache": True
        }),
    ],
)
@pytest.mark.parametrize(("force"), [
    (True, {
        "_use_outdated_persisted_sections": True
    }),
    (False, {}),
])
@pytest.mark.usefixtures("scenario")
def test_mode_inventory_caching(hosts, cache, force, monkeypatch, mocker):
    # Plugins have been loaded by module level fixture, disable loading in mode_inventory() to
    # improve speed of the test execution
    monkeypatch.setattr(cmk.base.inventory_plugins, "load_plugins", lambda x, y: None)

    kwargs = {}
    kwargs.update(hosts[1])
    kwargs.update(cache[1])
    kwargs.update(force[1])

    if cache[0] is None:
        kwargs["_may_use_cache_file"] = not hosts[0]

    _patch_data_source_run(mocker, **kwargs)

    config_cache = config.get_config_cache()

    if cache[0] is True:
        cmk.base.modes.check_mk.option_cache()
    elif cache[0] is False:
        cmk.base.modes.check_mk.option_no_cache()  # --no-cache

    options = {}
    if force[0]:
        options["force"] = True

    assert ABCDataSource._run.call_count == 0  # type: ignore[attr-defined]
    cmk.base.modes.check_mk.mode_inventory(options, hosts[0])

    # run() has to be called once for each requested host
    if hosts[0] == []:
        valid_hosts = config_cache.all_active_realhosts()
        valid_hosts = valid_hosts.union(config_cache.all_active_clusters())
    else:
        valid_hosts = hosts[0]

    num_runs = (len([h for h in valid_hosts if not config_cache.get_host_config(h).is_cluster]) * 2)

    assert ABCDataSource._run.call_count == num_runs  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("patch_data_source_run")
def test_mode_inventory_as_check():
    with cmk_debug_enabled():
        exit_code = cmk.base.modes.check_mk.mode_inventory_as_check({}, "ds-test-host1")

    assert exit_code == 0
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_marked_hosts(mocker):
    _patch_data_source_run(mocker, _max_cachefile_age=120)  # inventory_max_cachefile_age
    # TODO: First configure auto discovery to make this test really work
    cmk.base.modes.check_mk.mode_discover_marked_hosts()
    # assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_check_discovery_default(mocker):
    _patch_data_source_run(mocker, _max_cachefile_age=0)
    with cmk_debug_enabled():
        assert cmk.base.modes.check_mk.mode_check_discovery("ds-test-host1") == 1
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_check_discovery_cached(mocker):
    _patch_data_source_run(
        mocker,
        _max_cachefile_age=120,
        _use_outdated_cache_file=True,
        _may_use_cache_file=True,
    )

    cmk.base.modes.check_mk.option_cache()
    with cmk_debug_enabled():
        assert cmk.base.modes.check_mk.mode_check_discovery("ds-test-host1") == 1
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_all_hosts(mocker):
    _patch_data_source_run(mocker, _may_use_cache_file=True, _max_cachefile_age=120)
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, [])
    active_real_hosts = config.get_config_cache().all_active_realhosts()
    assert ABCDataSource._run.call_count == len(active_real_hosts) * 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_explicit_hosts(mocker):
    # TODO: Is it correct that no cache is used here?
    _patch_data_source_run(mocker, _max_cachefile_age=0)
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_explicit_hosts_cache(mocker):
    _patch_data_source_run(
        mocker,
        _max_cachefile_age=120,
        _may_use_cache_file=True,
        _use_outdated_cache_file=True,
    )
    cmk.base.modes.check_mk.option_cache()
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_explicit_hosts_no_cache(mocker):
    _patch_data_source_run(mocker, _no_cache=True, _max_cachefile_age=0)
    cmk.base.modes.check_mk.option_no_cache()  # --no-cache
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("patch_data_source_run")
def test_mode_check_explicit_host():
    cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_check_explicit_host_cache(mocker):
    _patch_data_source_run(mocker, _may_use_cache_file=True, _use_outdated_cache_file=True)
    cmk.base.modes.check_mk.option_cache()
    cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_check_explicit_host_no_cache(mocker):
    _patch_data_source_run(mocker, _no_cache=True, _max_cachefile_age=0)
    cmk.base.modes.check_mk.option_no_cache()  # --no-cache
    cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("patch_data_source_run")
def test_mode_dump_agent_explicit_host(capsys):
    cmk.base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.usefixtures("scenario")
def test_mode_dump_agent_explicit_host_cache(mocker, capsys):
    _patch_data_source_run(mocker, _may_use_cache_file=True, _use_outdated_cache_file=True)
    cmk.base.modes.check_mk.option_cache()
    cmk.base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.usefixtures("scenario")
def test_mode_dump_agent_explicit_host_no_cache(mocker, capsys):
    _patch_data_source_run(mocker, _no_cache=True, _max_cachefile_age=0)
    cmk.base.modes.check_mk.option_no_cache()  # --no-cache
    cmk.base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("scan"),
    [
        (
            "@noscan",
            {
                "do_snmp_scan": False,
                "_may_use_cache_file": True,
                "_max_cachefile_age": 120,
                "_use_outdated_cache_file": True,
            },
        ),
        (
            "@scan",
            {
                "do_snmp_scan": True,
                "_may_use_cache_file": False,
                "_max_cachefile_age": 0,
            },
        ),
    ],
)
@pytest.mark.parametrize(
    ("raise_errors"),
    [
        ("@raiseerrors", {
            "on_error": "raise"
        }),
        (None, {
            "on_error": "ignore"
        }),
    ],
)
@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("reset_log_level")
def test_automation_try_discovery_caching(scan, raise_errors, mocker):
    kwargs = {}
    kwargs.update(scan[1])
    kwargs.update(raise_errors[1])
    _patch_data_source_run(mocker, **kwargs)

    args = [scan[0]]
    if raise_errors[0] is not None:
        args.append(raise_errors[0])
    args.append("ds-test-host1")

    cmk.base.automations.check_mk.AutomationTryDiscovery().execute(args)
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("raise_errors"),
    [
        ("@raiseerrors", {
            "on_error": "raise"
        }),
        (None, {
            "on_error": "ignore"
        }),
    ],
)
@pytest.mark.parametrize(("scan"), [
    (None, {
        "do_snmp_scan": False
    }),
    ("@scan", {
        "do_snmp_scan": True
    }),
])
@pytest.mark.parametrize(
    ("cache"),
    [
        (
            "@cache",
            {
                "_max_cachefile_age": 120
            },
        ),  # TODO: Why not _may_use_cache_file=True? like try-discovery
        (None, {
            "_max_cachefile_age": 0
        }),
    ],
)
@pytest.mark.usefixtures("scenario")
def test_automation_discovery_caching(scan, cache, raise_errors, mocker):
    kwargs = {}
    kwargs.update(raise_errors[1])
    kwargs.update(scan[1])
    kwargs.update(cache[1])

    _patch_data_source_run(mocker, **kwargs)

    args = []
    if raise_errors[0] is not None:
        args.append(raise_errors[0])
    if scan[0] is not None:
        args.append(scan[0])
    if cache[0] is not None:
        args.append(cache[0])
    args += ["fixall", "ds-test-host1"]
    cmk.base.automations.check_mk.AutomationDiscovery().execute(args)
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("patch_data_source_run")
def test_automation_diag_host_caching():
    args = ["ds-test-host1", "agent", "127.0.0.1", "", "6557", "10", "5", "5", ""]
    cmk.base.automations.check_mk.AutomationDiagHost().execute(args)
    assert ABCDataSource._run.call_count == 2  # type: ignore[attr-defined]


# Globale Optionen:
# --cache    ->
# --no-cache ->
# --no-tcp   ->
# --usewalk  ->
# --force    ->

# Keepalive check
# Keepalive discovery
# TODO: Check the caching age for cluster hosts
