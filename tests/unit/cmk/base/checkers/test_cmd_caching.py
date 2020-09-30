#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# These tests verify the behaviour of the Checkmk base methods
# that do the actual checking/discovery/inventory work. Especially
# the default caching and handling of global options affecting the
# caching is checked

from functools import partial

import pytest  # type: ignore[import]

from testlib.utils import is_enterprise_repo
from testlib.base import Scenario
from testlib.debug_utils import cmk_debug_enabled

import cmk.utils.paths
from cmk.utils.log import logger

import cmk.base.automations
import cmk.base.automations.check_mk
import cmk.base.config as config
import cmk.base.inventory_plugins
import cmk.base.modes
import cmk.base.modes.check_mk
from cmk.base.checkers import ABCSource
from cmk.base.checkers.agent import AgentSource
from cmk.base.checkers.snmp import SNMPSource
import cmk.base.license_usage as license_usage

# TODO: These tests need to be tuned, because they involve a lot of checks being loaded which takes
# too much time.

# TODO (mo): now it's worse, we need to load all checks. remove this with CMK-4295
#            after removing this, bring back the commented line below.


@pytest.fixture(autouse=True)
def mock_license_usage(monkeypatch):
    monkeypatch.setattr(license_usage, "try_history_update", lambda: None)


@pytest.fixture(scope="module", autouse=True)
def enable_debug_mode():
    # `debug.disabled()` hides exceptions and makes it
    # *impossible* to debug anything.
    with cmk_debug_enabled():
        yield


@pytest.fixture(name="scenario")
def scenario_fixture(monkeypatch):
    test_hosts = ["ds-test-host1", "ds-test-host2", "ds-test-node1", "ds-test-node2"]

    ts = Scenario()

    if is_enterprise_repo():
        ts.set_option("monitoring_core", "cmc")
    else:
        ts.set_option("monitoring_core", "nagios")

    for h in test_hosts:
        ts.add_host(h)

    ts.set_option("ipaddresses", dict((h, "127.0.0.1") for h in test_hosts))
    ts.add_cluster("ds-test-cluster1", nodes=["ds-test-node1", "ds-test-node2"])
    ts.fake_standard_linux_agent_output(*test_hosts)

    return ts.apply(monkeypatch)


@pytest.fixture
def reset_log_level():
    level = logger.getEffectiveLevel()
    yield
    logger.setLevel(level)


def _patch_data_source(mocker, **kwargs):
    defaults = {
        "maybe": False,
        "use_outdated": False,
        "max_age": 0,  # check_max_cachefile_age
        "disabled": False,
        "use_outdated_persisted_sections": False,
        "on_error": "raise",
        "_use_snmpwalk_cache": True,
        "_ignore_check_interval": True,
    }
    defaults.update(kwargs)

    def parse(self, *args, callback, **kwargs):
        assert isinstance(self, ABCSource), repr(self)

        file_cache = self._make_file_cache()
        assert file_cache.disabled == defaults["disabled"]
        assert file_cache.use_outdated == defaults["use_outdated"]
        assert file_cache.max_age == defaults["max_age"]

        if isinstance(self, AgentSource):
            assert (
                self.use_outdated_persisted_sections == defaults["use_outdated_persisted_sections"])

        elif isinstance(self, SNMPSource):
            assert self.on_snmp_scan_error == defaults["on_error"]
            assert self.use_snmpwalk_cache == defaults["_use_snmpwalk_cache"]
            assert self.ignore_check_interval == defaults["_ignore_check_interval"]

        result = callback(self, *args, **kwargs)
        if result.is_error():
            raise result.error
        return result

    mocker.patch.object(
        ABCSource,
        "parse",
        autospec=True,
        side_effect=partial(parse, callback=ABCSource.parse),
    )


@pytest.fixture
def patch_data_source(mocker):
    _patch_data_source(mocker)


# When called without hosts, it uses all hosts and defaults to using the data source cache
# When called with an explicit list of hosts the cache is not used by default, the option
# --cache enables it and --no-cache enforce never to use it
@pytest.mark.parametrize(
    ("hosts"),
    [
        (
            ["ds-test-host1"],
            {
                "max_age": 0
            },
        ),
        (
            ["ds-test-cluster1"],
            {
                "max_age": 90
            },
        ),
        ([], {}),
    ],
    ids=["host", "cluster", "empty"],
)
@pytest.mark.parametrize(
    ("cache"),
    [
        (None, {}),
        (True, {
            "maybe": True,
            "use_outdated": True
        }),
        (False, {
            "maybe": False,
            "disabled": True
        }),
    ],
    ids=["cache=None", "cache=True", "cache=False"],
)
@pytest.mark.parametrize(
    ("force"),
    [
        (True, {
            "use_outdated_persisted_sections": True
        }),
        (False, {}),
    ],
    ids=["force=True", "force=False"],
)
@pytest.mark.usefixtures("scenario")
def test_mode_inventory_caching(hosts, cache, force, monkeypatch, mocker):

    kwargs = {}
    kwargs.update(hosts[1])
    kwargs.update(cache[1])
    kwargs.update(force[1])

    if cache[0] is None:
        kwargs["maybe"] = not hosts[0]

    _patch_data_source(mocker, **kwargs)

    config_cache = config.get_config_cache()

    if cache[0] is True:
        cmk.base.modes.check_mk.option_cache()
    elif cache[0] is False:
        cmk.base.modes.check_mk.option_no_cache()  # --no-cache

    options = {}
    if force[0]:
        options["force"] = True

    assert ABCSource.parse.call_count == 0  # type: ignore[attr-defined]
    cmk.base.modes.check_mk.mode_inventory(options, hosts[0])

    # run() has to be called once for each requested host
    if hosts[0] == []:
        valid_hosts = config_cache.all_active_realhosts()
        valid_hosts = valid_hosts.union(config_cache.all_active_clusters())
    else:
        valid_hosts = hosts[0]

    num_runs = (len([h for h in valid_hosts if not config_cache.get_host_config(h).is_cluster]) * 2)

    assert ABCSource.parse.call_count == num_runs  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("patch_data_source")
def test_mode_inventory_as_check():
    assert cmk.base.modes.check_mk.mode_inventory_as_check({}, "ds-test-host1") == 0
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_marked_hosts(mocker):
    _patch_data_source(mocker, max_age=120)  # inventory_max_cachefile_age
    # TODO: First configure auto discovery to make this test really work
    cmk.base.modes.check_mk.mode_discover_marked_hosts()
    # assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.usefixtures("scenario")
def test_mode_check_discovery_default(mocker):
    _patch_data_source(mocker, max_age=0)
    assert cmk.base.modes.check_mk.mode_check_discovery("ds-test-host1") == 1
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.usefixtures("scenario")
def test_mode_check_discovery_cached(mocker):
    _patch_data_source(
        mocker,
        max_age=120,
        use_outdated=True,
        maybe=True,
    )

    cmk.base.modes.check_mk.option_cache()
    assert cmk.base.modes.check_mk.mode_check_discovery("ds-test-host1") == 1
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.usefixtures("scenario")
def test_mode_discover_all_hosts(mocker):
    _patch_data_source(mocker, maybe=True, max_age=120)
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, [])
    active_real_hosts = config.get_config_cache().all_active_realhosts()
    assert ABCSource.parse.call_count == (  # type: ignore[attr-defined]
        len(active_real_hosts) * 2)


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.usefixtures("scenario")
def test_mode_discover_explicit_hosts(mocker):
    # TODO: Is it correct that no cache is used here?
    _patch_data_source(mocker, max_age=0)
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.usefixtures("scenario")
def test_mode_discover_explicit_hosts_cache(mocker):
    _patch_data_source(
        mocker,
        max_age=120,
        maybe=True,
        use_outdated=True,
    )
    cmk.base.modes.check_mk.option_cache()
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.usefixtures("scenario")
def test_mode_discover_explicit_hosts_no_cache(mocker):
    _patch_data_source(mocker, disabled=True, max_age=0)
    cmk.base.modes.check_mk.option_no_cache()  # --no-cache
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("patch_data_source")
def test_mode_check_explicit_host():
    cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_check_explicit_host_cache(mocker):
    _patch_data_source(mocker, maybe=True, use_outdated=True)
    cmk.base.modes.check_mk.option_cache()
    cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_check_explicit_host_no_cache(mocker):
    _patch_data_source(mocker, disabled=True, max_age=0)
    cmk.base.modes.check_mk.option_no_cache()  # --no-cache
    cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("patch_data_source")
def test_mode_dump_agent_explicit_host(capsys):
    cmk.base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.usefixtures("scenario")
def test_mode_dump_agent_explicit_host_cache(mocker, capsys):
    _patch_data_source(mocker, maybe=True, use_outdated=True)
    cmk.base.modes.check_mk.option_cache()
    cmk.base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.usefixtures("scenario")
def test_mode_dump_agent_explicit_host_no_cache(mocker, capsys):
    _patch_data_source(mocker, disabled=True, max_age=0)
    cmk.base.modes.check_mk.option_no_cache()  # --no-cache
    cmk.base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("scan"),
    [
        (
            "@noscan",
            {
                "maybe": True,
                "max_age": 120,
                "use_outdated": True,
            },
        ),
        (
            "@scan",
            {
                "maybe": False,
                "max_age": 0,
            },
        ),
    ],
    ids=["scan=@noscan", "scan=@scan"],
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
    ids=["raise_errors=@raiseerrors", "raise_errors=None"],
)
@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("reset_log_level")
def test_automation_try_discovery_caching(scan, raise_errors, mocker):
    kwargs = {}
    kwargs.update(scan[1])
    kwargs.update(raise_errors[1])
    _patch_data_source(mocker, **kwargs)

    args = [scan[0]]
    if raise_errors[0] is not None:
        args.append(raise_errors[0])
    args.append("ds-test-host1")

    cmk.base.automations.check_mk.AutomationTryDiscovery().execute(args)
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


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
    ids=["raise_errors=@raiserrors", "raise_errors=none"],
)
@pytest.mark.parametrize(
    ("scan"),
    [
        None,
        "@scan",
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.usefixtures("scenario")
def test_automation_discovery_caching(raise_errors, scan, mocker):
    kwargs = {}
    kwargs.update(raise_errors[1])
    # The next options come from the call to `_set_cache_opts_of_checkers()`
    # in `AutomationDiscovery`.
    maybe = scan != "@scan"
    kwargs.update(maybe=maybe)
    kwargs.update(use_outdated=maybe)
    kwargs.update(max_age=120 if maybe else 0)

    _patch_data_source(mocker, **kwargs)

    args = []
    if raise_errors[0] is not None:
        args.append(raise_errors[0])
    if scan is not None:
        args.append(scan)

    args += ["fixall", "ds-test-host1"]
    cmk.base.automations.check_mk.AutomationDiscovery().execute(args)
    assert ABCSource.parse.call_count == 2  # type: ignore[attr-defined]


# Globale Optionen:
# --cache    ->
# --no-cache ->
# --no-tcp   ->
# --usewalk  ->
# --force    ->

# Keepalive check
# Keepalive discovery
# TODO: Check the caching age for cluster hosts
