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

import pytest

from tests.testlib.base import Scenario
from tests.testlib.utils import is_enterprise_repo

import cmk.utils.paths
from cmk.utils.log import logger
from cmk.utils.type_defs import HostName

from cmk.core_helpers.cache import MaxAge

import cmk.base.automations
import cmk.base.automations.check_mk
import cmk.base.config as config
import cmk.base.modes
import cmk.base.modes.check_mk
from cmk.base.sources import Source
from cmk.base.sources.agent import AgentSource
from cmk.base.sources.snmp import SNMPSource
from cmk.base.sources.tcp import TCPSource


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
        "max_age": config.max_cachefile_age(),
        "disabled": False,
        "use_only_cache": False,
        "use_outdated_persisted_sections": False,
        "on_error": "raise",
    }
    defaults.update(kwargs)

    def parse(self, *args, callback, **kwargs):
        assert isinstance(self, Source), repr(self)

        file_cache = self._make_file_cache()

        assert file_cache.use_outdated == defaults["use_outdated"]
        assert file_cache.max_age == defaults["max_age"]

        if isinstance(self, TCPSource):
            assert self.use_only_cache == defaults["use_only_cache"]
        if isinstance(self, AgentSource):
            assert (
                self.use_outdated_persisted_sections == defaults["use_outdated_persisted_sections"]
            )

        elif isinstance(self, SNMPSource):
            assert self._on_snmp_scan_error == defaults["on_error"]

        result = callback(self, *args, **kwargs)
        if result.is_error():
            raise result.error
        return result

    mocker.patch.object(
        Source,
        "parse",
        autospec=True,
        side_effect=partial(parse, callback=Source.parse),
    )


@pytest.fixture
def patch_data_source(mocker):
    _patch_data_source(mocker)


@pytest.fixture
def without_inventory_plugins(monkeypatch):
    monkeypatch.setattr(cmk.base.api.agent_based.register, "iter_all_inventory_plugins", lambda: ())


# When called without hosts, it uses all hosts and defaults to using the data source cache
# When called with an explicit list of hosts the cache is not used by default, the option
# --cache enables it and --no-cache enforce never to use it
@pytest.mark.parametrize(
    ("hosts"),
    [
        (
            ["ds-test-host1"],
            {
                "max_age": config.max_cachefile_age(),
            },
        ),
        (
            ["ds-test-cluster1"],
            {
                "max_age": config.max_cachefile_age(),
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
        (True, {"maybe": True, "use_outdated": True}),
        (False, {"maybe": False, "disabled": True}),
    ],
    ids=["cache=None", "cache=True", "cache=False"],
)
@pytest.mark.parametrize(
    ("force"),
    [
        (True, {"use_outdated_persisted_sections": True}),
        (False, {}),
    ],
    ids=["force=True", "force=False"],
)
@pytest.mark.usefixtures("scenario", "without_inventory_plugins")
def test_mode_inventory_caching(hosts, cache, force, mocker) -> None:
    kwargs = {}
    kwargs.update(hosts[1])
    kwargs.update(cache[1])
    kwargs.update(force[1])

    if cache[0] is None:
        kwargs["maybe"] = not hosts[0]

    _patch_data_source(mocker, **kwargs)

    config_cache = config.get_config_cache()

    options: cmk.base.modes.check_mk._InventoryOptions = {}
    if cache[0] is True:
        options["cache"] = True  # --cache
    elif cache[0] is False:
        options["no-cache"] = True  # --no-cache

    if force[0]:
        options["force"] = True

    assert Source.parse.call_count == 0  # type: ignore[attr-defined]
    cmk.base.modes.check_mk.mode_inventory(options, hosts[0])

    # run() has to be called once for each requested host
    if hosts[0] == []:
        valid_hosts = config_cache.all_active_realhosts()
        valid_hosts = valid_hosts.union(config_cache.all_active_clusters())
    else:
        valid_hosts = hosts[0]

    num_runs = len([h for h in valid_hosts if not config_cache.get_host_config(h).is_cluster]) * 2

    assert Source.parse.call_count == num_runs  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("patch_data_source")
@pytest.mark.usefixtures("without_inventory_plugins")
def test_mode_inventory_as_check() -> None:
    assert cmk.base.modes.check_mk.mode_inventory_as_check({}, HostName("ds-test-host1")) == 0
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_marked_hosts(mocker) -> None:
    _patch_data_source(
        mocker,
        max_age=config.max_cachefile_age(),
    )  # inventory_max_cachefile_age
    # TODO: First configure auto discovery to make this test really work
    cmk.base.modes.check_mk.mode_discover_marked_hosts({})
    # assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("fix_register")
@pytest.mark.usefixtures("scenario")
def test_mode_check_discovery_default(mocker) -> None:
    _patch_data_source(mocker, max_age=MaxAge(checking=0, discovery=0, inventory=120))
    assert cmk.base.modes.check_mk.mode_check_discovery({}, HostName("ds-test-host1")) == 1
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("fix_register")
@pytest.mark.usefixtures("scenario")
def test_mode_check_discovery_cached(mocker) -> None:
    _patch_data_source(
        mocker,
        max_age=config.max_cachefile_age(),
        use_outdated=True,
        maybe=True,
    )

    assert (
        cmk.base.modes.check_mk.mode_check_discovery(
            {
                "cache": True,
            },
            HostName("ds-test-host1"),
        )
        == 1
    )
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_all_hosts(mocker) -> None:
    _patch_data_source(
        mocker,
        maybe=True,
        use_outdated=True,
        max_age=config.max_cachefile_age(),
    )
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, [])
    active_real_hosts = config.get_config_cache().all_active_realhosts()
    assert Source.parse.call_count == (len(active_real_hosts) * 2)  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_explicit_hosts(mocker) -> None:
    # TODO: Is it correct that no cache is used here?
    _patch_data_source(mocker, max_age=config.max_cachefile_age())
    cmk.base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_explicit_hosts_cache(mocker) -> None:
    _patch_data_source(
        mocker,
        max_age=config.max_cachefile_age(),
        maybe=True,
        use_outdated=True,
    )
    cmk.base.modes.check_mk.mode_discover(
        {
            "cache": True,  # --cache
            "discover": 1,
        },
        ["ds-test-host1"],
    )
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_discover_explicit_hosts_no_cache(mocker) -> None:
    _patch_data_source(mocker, disabled=True, max_age=config.max_cachefile_age())
    cmk.base.modes.check_mk.mode_discover(
        {
            "no-cache": True,  # --no-cache
            "discover": 1,
        },
        ["ds-test-host1"],
    )
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
@pytest.mark.usefixtures("patch_data_source")
def test_mode_check_explicit_host() -> None:
    cmk.base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_check_explicit_host_cache(mocker) -> None:
    _patch_data_source(mocker, maybe=True, use_outdated=True)
    cmk.base.modes.check_mk.mode_check(
        {
            "cache": True,  # --cache
        },
        ["ds-test-host1"],
    )
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_check_explicit_host_no_cache(mocker) -> None:
    _patch_data_source(
        mocker,
        disabled=True,
        max_age=config.max_cachefile_age(),
    )
    cmk.base.modes.check_mk.mode_check(
        {
            "no-cache": True,  # --no-cache
        },
        ["ds-test-host1"],
    )
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.usefixtures("scenario")
def test_mode_dump_agent_explicit_host(mocker, capsys) -> None:
    _patch_data_source(mocker, max_age=config.max_cachefile_age())
    cmk.base.modes.check_mk.mode_dump_agent({}, HostName("ds-test-host1"))
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.usefixtures("scenario")
def test_mode_dump_agent_explicit_host_cache(mocker, capsys) -> None:
    _patch_data_source(
        mocker,
        max_age=config.max_cachefile_age(),
        maybe=True,
        use_outdated=True,
    )
    cmk.base.modes.check_mk.mode_dump_agent(
        {
            "cache": True,  # --cache
        },
        HostName("ds-test-host1"),
    )
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.usefixtures("scenario")
def test_mode_dump_agent_explicit_host_no_cache(mocker, capsys) -> None:
    _patch_data_source(mocker, disabled=True, max_age=config.max_cachefile_age())
    cmk.base.modes.check_mk.mode_dump_agent(
        {
            "no-cache": True,  # --no-cache
        },
        HostName("ds-test-host1"),
    )
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]
    assert "<<<check_mk>>>" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("scan"),
    [
        (
            "@noscan",
            {
                "disabled": False,
                "use_only_chache": True,  # TCP
                "max_age": config.max_cachefile_age(),
                "use_outdated": True,
            },
        ),
        (
            "@scan",
            {
                "disabled": False,  # TCP
                "use_only_chache": True,  # TCP
                "max_age": config.max_cachefile_age(),
                "use_outdated": True,
            },
        ),
    ],
    ids=["scan=@noscan", "scan=@scan"],
)
@pytest.mark.parametrize(
    ("raise_errors"),
    [
        ("@raiseerrors", {"on_error": "raise"}),
        (None, {"on_error": "ignore"}),
    ],
    ids=["raise_errors=@raiseerrors", "raise_errors=None"],
)
@pytest.mark.usefixtures("scenario", "reset_log_level", "initialised_item_state")
def test_automation_try_discovery_caching(scan, raise_errors, mocker) -> None:
    kwargs = {}
    kwargs.update(scan[1])
    kwargs.update(raise_errors[1])
    _patch_data_source(mocker, **kwargs)

    args = [scan[0]]
    if raise_errors[0] is not None:
        args.append(raise_errors[0])
    args.append("ds-test-host1")

    cmk.base.automations.check_mk.AutomationTryDiscovery().execute(args)
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("raise_errors"),
    [
        ("@raiseerrors", {"on_error": "raise"}),
        (None, {"on_error": "ignore"}),
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
@pytest.mark.usefixtures("scenario")
def test_automation_discovery_caching(raise_errors, scan, mocker) -> None:
    kwargs = {}
    kwargs.update(raise_errors[1])
    # The next options come from the call to `_set_cache_opts_of_checkers()`
    # in `AutomationDiscovery`.
    kwargs.update(
        use_outdated=True,
        max_age=config.max_cachefile_age(),
    )

    _patch_data_source(mocker, **kwargs)

    args = []
    if raise_errors[0] is not None:
        args.append(raise_errors[0])
    if scan is not None:
        args.append(scan)

    args += ["fixall", "ds-test-host1"]
    cmk.base.automations.check_mk.AutomationDiscovery().execute(args)
    assert Source.parse.call_count == 2  # type: ignore[attr-defined]


# Globale Optionen:
# --cache    ->
# --no-cache ->
# --no-tcp   ->
# --usewalk  ->
# --force    ->

# Keepalive check
# Keepalive discovery
# TODO: Check the caching age for cluster hosts
