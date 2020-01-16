#!/usr/bin/env python
# pylint: disable=redefined-outer-name
# These tests verify the behaviour of the Check_MK base methods
# that do the actual checking/discovery/inventory work. Especially
# the default caching and handling of global options affecting the
# caching is checked

from __future__ import print_function
from pathlib2 import Path
import pytest  # type: ignore

from testlib import repo_path
from testlib.base import Scenario
from testlib import CheckManager, InventoryPluginManager

import cmk.utils.paths
import cmk.base.config as config
import cmk.base.modes
import cmk.base.automations
import cmk.base.inventory_plugins
from cmk.utils.log import logger

# TODO: These tests need to be tuned, because they involve a lot of checks being loaded which takes
# too much time.


# Load some common checks to have at least some for the test execution
# Modes that have needs_checks=True set would miss the checks
# without this fixtures
@pytest.fixture(scope="module", autouse=True)
def load_plugins():
    CheckManager().load(["df", "cpu", "chrony", "lnx_if", "livestatus_status", "omd_status"])
    InventoryPluginManager().load()


@pytest.fixture()
def test_cfg(monkeypatch):
    test_hosts = ["ds-test-host1", "ds-test-host2", "ds-test-node1", "ds-test-node2"]

    ts = Scenario()

    for h in test_hosts:
        ts.add_host(h)

    ts.set_option("ipaddresses", dict((h, "127.0.0.1") for h in test_hosts))
    ts.add_cluster("ds-test-cluster1", nodes=["ds-test-node1", "ds-test-node2"])

    ts.set_ruleset("datasource_programs", [
        ('cat %s/<HOST>' % cmk.utils.paths.tcp_cache_dir, [], test_hosts, {}),
    ])

    with open("%s/tests/integration/cmk/base/test-files/linux-agent-output" % repo_path()) as f:
        linux_agent_output = f.read().decode("utf-8")

    for h in test_hosts:
        cache_path = Path(cmk.utils.paths.tcp_cache_dir, h)
        cache_path.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member

        with cache_path.open("w", encoding="utf-8") as f:
            f.write(linux_agent_output)

    return ts.apply(monkeypatch)


@pytest.fixture(scope="function", autouse=True)
def restore_default_caching_config():
    assert hasattr(cmk.base.data_sources.abstract.DataSource, "_may_use_cache_file")
    cmk.base.data_sources.abstract.DataSource._may_use_cache_file = False

    assert hasattr(cmk.base.data_sources.abstract.DataSource, "_no_cache")
    cmk.base.data_sources.abstract.DataSource._no_cache = False

    assert hasattr(cmk.base.data_sources.abstract.DataSource, "_use_outdated_persisted_sections")
    cmk.base.data_sources.abstract.CheckMKAgentDataSource._use_outdated_persisted_sections = False

    assert hasattr(cmk.base.data_sources.abstract.DataSource, "_use_outdated_cache_file")
    cmk.base.data_sources.abstract.DataSource._use_outdated_cache_file = False


_counter_run = 0


def _patch_data_source_run(monkeypatch, **kwargs):
    global _counter_run
    _counter_run = 0

    defaults = {
        "_may_use_cache_file": False,
        "_use_outdated_cache_file": False,
        "_max_cachefile_age": 0,  # check_max_cachefile_age
        "_no_cache": False,
        "_use_outdated_persisted_sections": False,
        "_do_snmp_scan": False,
        "_on_error": "raise",
        "_use_snmpwalk_cache": True,
        "_ignore_check_interval": True,
    }
    defaults.update(kwargs)

    def _run(self, hostname, ipaddress, get_raw_data):
        assert self._may_use_cache_file == defaults["_may_use_cache_file"]
        assert self._no_cache == defaults["_no_cache"]
        assert self._max_cachefile_age == defaults["_max_cachefile_age"]
        assert self._use_outdated_cache_file == defaults["_use_outdated_cache_file"]

        if isinstance(self, cmk.base.data_sources.abstract.CheckMKAgentDataSource):
            assert self._use_outdated_persisted_sections == defaults[
                "_use_outdated_persisted_sections"]

        elif isinstance(self, cmk.base.data_sources.SNMPDataSource):
            assert self._do_snmp_scan == defaults["_do_snmp_scan"]
            assert self._on_error == defaults["_on_error"]
            assert self._use_snmpwalk_cache == defaults["_use_snmpwalk_cache"]
            assert self._ignore_check_interval == defaults["_ignore_check_interval"]

        result = self._orig_run(hostname, ipaddress, get_raw_data)

        global _counter_run
        _counter_run += 1

        return result

    monkeypatch.setattr(cmk.base.data_sources.abstract.DataSource,
                        "_orig_run",
                        cmk.base.data_sources.abstract.DataSource._run,
                        raising=False)
    monkeypatch.setattr(cmk.base.data_sources.abstract.DataSource, "_run", _run)


# When called without hosts, it uses all hosts and defaults to using the data source cache
# When called with an explicit list of hosts the cache is not used by default, the option
# --cache enables it and --no-cache enforce never to use it
@pytest.mark.parametrize(("hosts"), [
    (["ds-test-host1"], {
        "_max_cachefile_age": 0
    }),
    (["ds-test-cluster1"], {
        "_max_cachefile_age": 90
    }),
    ([], {}),
])
@pytest.mark.parametrize(("cache"), [
    (None, {}),
    (True, {
        "_may_use_cache_file": True,
        "_use_outdated_cache_file": True
    }),
    (False, {
        "_may_use_cache_file": False,
        "_no_cache": True
    }),
])
@pytest.mark.parametrize(("force"), [
    (True, {
        "_use_outdated_persisted_sections": True
    }),
    (False, {}),
])
def test_mode_inventory_caching(test_cfg, hosts, cache, force, monkeypatch):
    # Plugins have been loaded by module level fixture, disable loading in mode_inventory() to
    # improve speed of the test execution
    monkeypatch.setattr(cmk.base.inventory_plugins, "load_plugins", lambda x, y: None)

    kwargs = {}
    kwargs.update(hosts[1])
    kwargs.update(cache[1])
    kwargs.update(force[1])

    if cache[0] is None:
        kwargs["_may_use_cache_file"] = not hosts[0]

    _patch_data_source_run(monkeypatch, **kwargs)

    config_cache = config.get_config_cache()

    try:
        if cache[0] is True:
            cmk.base.modes.check_mk.option_cache()
        elif cache[0] is False:
            cmk.base.modes.check_mk.option_no_cache()  # --no-cache

        options = {}
        if force[0]:
            options["force"] = True

        assert _counter_run == 0
        cmk.base.modes.check_mk.mode_inventory(options, hosts[0])

        # run() has to be called once for each requested host
        if hosts[0] == []:
            valid_hosts = config_cache.all_active_realhosts()
            valid_hosts = valid_hosts.union(config_cache.all_active_clusters())
        else:
            valid_hosts = hosts[0]

        num_runs = len([h for h in valid_hosts if not config_cache.get_host_config(h).is_cluster
                       ]) * 2

        assert _counter_run == num_runs
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk.base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_inventory_as_check(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch)
    assert cmk.base.modes.check_mk.mode_inventory_as_check({}, "ds-test-host1") == 0
    assert _counter_run == 2


def test_mode_discover_marked_hosts(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch, _max_cachefile_age=120)  # inventory_max_cachefile_age
    # TODO: First configure auto discovery to make this test really work
    cmk.base.modes.check_mk.mode_discover_marked_hosts()
    #assert _counter_run == 2


def test_mode_check_discovery_default(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch, _max_cachefile_age=0)
    assert cmk.base.modes.check_mk.mode_check_discovery("ds-test-host1") == 1
    assert _counter_run == 2


def test_mode_check_discovery_cached(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch,
                           _max_cachefile_age=120,
                           _use_outdated_cache_file=True,
                           _may_use_cache_file=True)

    try:
        cmk.base.modes.check_mk.option_cache()
        assert cmk.base.modes.check_mk.mode_check_discovery("ds-test-host1") == 1
        assert _counter_run == 2
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk.base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_discover_all_hosts(test_cfg, monkeypatch):
    config_cache = config.get_config_cache()
    _patch_data_source_run(monkeypatch, _may_use_cache_file=True, _max_cachefile_age=120)
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, [])
    assert _counter_run == len(config_cache.all_active_realhosts()) * 2


def test_mode_discover_explicit_hosts(test_cfg, monkeypatch):
    # TODO: Is it correct that no cache is used here?
    _patch_data_source_run(monkeypatch, _max_cachefile_age=0)
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert _counter_run == 2


def test_mode_discover_explicit_hosts_cache(test_cfg, monkeypatch):
    try:
        _patch_data_source_run(monkeypatch,
                               _max_cachefile_age=120,
                               _may_use_cache_file=True,
                               _use_outdated_cache_file=True)
        cmk.base.modes.check_mk.option_cache()
        cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
        assert _counter_run == 2
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk.base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_discover_explicit_hosts_no_cache(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch, _no_cache=True, _max_cachefile_age=0)
    cmk.base.modes.check_mk.option_no_cache()  # --no-cache
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert _counter_run == 2


def test_mode_check_explicit_host(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch)
    cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert _counter_run == 2


def test_mode_check_explicit_host_cache(test_cfg, monkeypatch):
    try:
        _patch_data_source_run(monkeypatch, _may_use_cache_file=True, _use_outdated_cache_file=True)
        cmk.base.modes.check_mk.option_cache()
        cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
        assert _counter_run == 2
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk.base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_check_explicit_host_no_cache(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch, _no_cache=True, _max_cachefile_age=0)
    cmk.base.modes.check_mk.option_no_cache()  # --no-cache
    cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert _counter_run == 2


def test_mode_dump_agent_explicit_host(test_cfg, monkeypatch, capsys):
    _patch_data_source_run(monkeypatch)
    cmk.base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert _counter_run == 2
    assert "<<<check_mk>>>" in capsys.readouterr().out


def test_mode_dump_agent_explicit_host_cache(test_cfg, monkeypatch, capsys):
    try:
        _patch_data_source_run(monkeypatch, _may_use_cache_file=True, _use_outdated_cache_file=True)
        cmk.base.modes.check_mk.option_cache()
        cmk.base.modes.check_mk.mode_dump_agent("ds-test-host1")
        assert _counter_run == 2
        assert "<<<check_mk>>>" in capsys.readouterr().out
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk.base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_dump_agent_explicit_host_no_cache(test_cfg, monkeypatch, capsys):
    _patch_data_source_run(monkeypatch, _no_cache=True, _max_cachefile_age=0)
    cmk.base.modes.check_mk.option_no_cache()  # --no-cache
    cmk.base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert _counter_run == 2
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.parametrize(("scan"), [
    ("@noscan", {
        "_do_snmp_scan": False,
        "_may_use_cache_file": True,
        "_max_cachefile_age": 120,
        "_use_outdated_cache_file": True,
    }),
    ("@scan", {
        "_do_snmp_scan": True,
        "_may_use_cache_file": False,
        "_max_cachefile_age": 0
    }),
])
@pytest.mark.parametrize(("raise_errors"), [
    ("@raiseerrors", {
        "_on_error": "raise"
    }),
    (None, {
        "_on_error": "ignore"
    }),
])
def test_automation_try_discovery_caching(test_cfg, scan, raise_errors, monkeypatch):
    kwargs = {}
    kwargs.update(scan[1])
    kwargs.update(raise_errors[1])

    args = [scan[0]]
    if raise_errors[0] is not None:
        args.append(raise_errors[0])
    args.append("ds-test-host1")

    _patch_data_source_run(monkeypatch, **kwargs)

    orig_level = logger.getEffectiveLevel()
    try:
        cmk.base.automations.check_mk.AutomationTryDiscovery().execute(args)
        assert _counter_run == 2
    finally:
        logger.setLevel(orig_level)


@pytest.mark.parametrize(("raise_errors"), [
    ("@raiseerrors", {
        "_on_error": "raise"
    }),
    (None, {
        "_on_error": "ignore"
    }),
])
@pytest.mark.parametrize(("scan"), [
    (None, {
        "_do_snmp_scan": False
    }),
    ("@scan", {
        "_do_snmp_scan": True
    }),
])
@pytest.mark.parametrize(
    ("cache"),
    [
        ("@cache", {
            "_max_cachefile_age": 120
        }),  # TODO: Why not _may_use_cache_file=True? like try-discovery
        (None, {
            "_max_cachefile_age": 0
        }),
    ])
def test_automation_discovery_caching(test_cfg, scan, cache, raise_errors, monkeypatch):
    kwargs = {}
    kwargs.update(raise_errors[1])
    kwargs.update(scan[1])
    kwargs.update(cache[1])

    args = []
    if raise_errors[0] is not None:
        args.append(raise_errors[0])
    if scan[0] is not None:
        args.append(scan[0])
    if cache[0] is not None:
        args.append(cache[0])

    args += ["fixall", "ds-test-host1"]

    _patch_data_source_run(monkeypatch, **kwargs)

    cmk.base.automations.check_mk.AutomationDiscovery().execute(args)
    assert _counter_run == 2


def test_automation_diag_host_caching(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch)

    args = ["ds-test-host1", "agent", "127.0.0.1", None, 6557, 10, 5, 5, None]
    cmk.base.automations.check_mk.AutomationDiagHost().execute(args)
    assert _counter_run == 2


# Globale Optionen:
# --cache    ->
# --no-cache ->
# --no-tcp   ->
# --usewalk  ->
# --force    ->

# Keepalive check
# Keepalive discovery
# TODO: Check the caching age for cluster hosts
