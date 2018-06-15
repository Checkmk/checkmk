#!/usr/bin/env python
# These tests verify the behaviour of the Check_MK base methods
# that do the actual checking/discovery/inventory work. Especially
# the default caching and handling of global options affecting the
# caching is checked

import pytest
from testlib import web, repo_path

import cmk_base.config as config
import cmk_base.modes
import cmk_base.automations

#
# INTEGRATION TESTS
#

@pytest.fixture(scope="module")
def test_cfg(web, site):
    print "Applying default config"
    web.add_host("ds-test-host1", attributes={
        "ipaddress": "127.0.0.1",
    })
    web.add_host("ds-test-host2", attributes={
        "ipaddress": "127.0.0.1",
    }
    )
    web.add_host("ds-test-node1", attributes={
        "ipaddress": "127.0.0.1",
    })
    web.add_host("ds-test-node2", attributes={
        "ipaddress": "127.0.0.1",
    })

    web.add_host("ds-test-cluster1", attributes={
        "ipaddress": "127.0.0.1",
        },
        cluster_nodes=[ "ds-test-node1", "ds-test-node2", ],
    )

    site.write_file("etc/check_mk/conf.d/ds-test-host.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ALL_HOSTS))\n")

    site.makedirs("var/check_mk/agent_output/")
    for h in [ "ds-test-host1", "ds-test-host2",
               "ds-test-node1", "ds-test-node2" ]:
        site.write_file("var/check_mk/agent_output/%s" % h,
            file("%s/tests/integration/cmk_base/test-files/linux-agent-output" % repo_path()).read())

    web.activate_changes()

    import cmk.debug
    cmk.debug.enable()

    # Needs to be done together, even when the checks are not directly needed
    import cmk_base.check_api as check_api
    config.load_all_checks(check_api.get_check_api_context)
    config.load()

    yield None

    #
    # Cleanup code
    #
    print "Cleaning up test config"

    cmk.debug.disable()

    site.delete_dir("var/check_mk/agent_output")
    site.delete_file("etc/check_mk/conf.d/ds-test-host.mk")

    web.delete_host("ds-test-host1")
    web.delete_host("ds-test-host2")
    web.delete_host("ds-test-node1")
    web.delete_host("ds-test-node2")
    web.delete_host("ds-test-cluster1")

    web.activate_changes()


@pytest.fixture(scope="function", autouse=True)
def restore_default_caching_config():
    assert hasattr(cmk_base.data_sources.abstract.DataSource, "_may_use_cache_file")
    cmk_base.data_sources.abstract.DataSource._may_use_cache_file = False

    assert hasattr(cmk_base.data_sources.abstract.DataSource, "_no_cache")
    cmk_base.data_sources.abstract.DataSource._no_cache = False

    assert hasattr(cmk_base.data_sources.abstract.DataSource, "_use_outdated_persisted_sections")
    cmk_base.data_sources.abstract.CheckMKAgentDataSource._use_outdated_persisted_sections = False

    assert hasattr(cmk_base.data_sources.abstract.DataSource, "_use_outdated_cache_file")
    cmk_base.data_sources.abstract.DataSource._use_outdated_cache_file = False


def _patch_data_source_run(monkeypatch, **kwargs):
    global _counter_run
    _counter_run = 0

    defaults = {
        "_may_use_cache_file"              : False,
        "_use_outdated_cache_file"         : False,
        "_max_cachefile_age"               : 0, # check_max_cachefile_age
        "_no_cache"                        : False,
        "_use_outdated_persisted_sections" : False,
        "_do_snmp_scan"                    : False,
        "_on_error"                        : "raise",
        "_use_snmpwalk_cache"              : True,
        "_ignore_check_interval"           : True,
    }
    defaults.update(kwargs)

    def run(self, hostname=None, ipaddress=None, get_raw_data=False):
        assert self._may_use_cache_file == defaults["_may_use_cache_file"]
        assert self._no_cache == defaults["_no_cache"]
        assert self._max_cachefile_age == defaults["_max_cachefile_age"]
        assert self._use_outdated_cache_file == defaults["_use_outdated_cache_file"]

        if isinstance(self, cmk_base.data_sources.abstract.CheckMKAgentDataSource):
            assert self._use_outdated_persisted_sections == defaults["_use_outdated_persisted_sections"]

        elif isinstance(self, cmk_base.data_sources.SNMPDataSource):
            assert self._do_snmp_scan == defaults["_do_snmp_scan"]
            assert self._on_error == defaults["_on_error"]
            assert self._use_snmpwalk_cache == defaults["_use_snmpwalk_cache"]
            assert self._ignore_check_interval == defaults["_ignore_check_interval"]

        result = self._run(hostname, ipaddress, get_raw_data)

        global _counter_run
        _counter_run += 1

        return result

    monkeypatch.setattr(cmk_base.data_sources.abstract.DataSource, "_run", cmk_base.data_sources.abstract.DataSource.run, raising=False)
    monkeypatch.setattr(cmk_base.data_sources.abstract.DataSource, "run", run)


# When called without hosts, it uses all hosts and defaults to using the data source cache
# When called with an explicit list of hosts the cache is not used by default, the option
# --cache enables it and --no-cache enforce never to use it
@pytest.mark.parametrize(("hosts"), [
    (["ds-test-host1"], {"_max_cachefile_age": 0}),
    (["ds-test-cluster1"], {"_max_cachefile_age": 90}),
    ([], {}),
])
@pytest.mark.parametrize(("cache"), [
    (None, {}),
    (True, {"_may_use_cache_file": True, "_use_outdated_cache_file": True}),
    (False, {"_may_use_cache_file": False, "_no_cache": True}),
])
@pytest.mark.parametrize(("force"), [
    (True, {"_use_outdated_persisted_sections": True}),
    (False, {}),
])
def test_mode_inventory_caching(test_cfg, hosts, cache, force, monkeypatch):
    kwargs = {}
    kwargs.update(hosts[1])
    kwargs.update(cache[1])
    kwargs.update(force[1])

    if cache[0] is None:
        if not hosts[0]:
            kwargs["_may_use_cache_file"] = True
        else:
            kwargs["_may_use_cache_file"] = False

    print kwargs

    _patch_data_source_run(monkeypatch, **kwargs)

    try:
        if cache[0] == True:
            cmk_base.modes.check_mk.option_cache()
        elif cache[0] == False:
            cmk_base.modes.check_mk.option_no_cache() # --no-cache

        options = {}
        if force[0]:
            options["force"] = True

        assert _counter_run == 0
        cmk_base.modes.check_mk.mode_inventory(options, hosts[0])

        # run() has to be called once for each requested host
        if hosts[0] == []:
            valid_hosts = config.all_active_realhosts()
            valid_hosts = valid_hosts.union(config.all_active_clusters())
        else:
            valid_hosts = hosts[0]

        num_runs = len([ h for h in valid_hosts
                         if not config.is_cluster(h) ])*2

        assert _counter_run == num_runs
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk_base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_inventory_as_check(test_cfg, monkeypatch, mock):
    _patch_data_source_run(monkeypatch)
    assert cmk_base.modes.check_mk.mode_inventory_as_check({}, "ds-test-host1") == 0
    assert _counter_run == 2


def test_mode_discover_marked_hosts(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch, _max_cachefile_age=120) # inventory_max_cachefile_age
    # TODO: First configure auto discovery to make this test really work
    cmk_base.modes.check_mk.mode_discover_marked_hosts()
    #assert _counter_run == 2


def test_mode_check_discovery_default(test_cfg, monkeypatch, mock):
    _patch_data_source_run(monkeypatch, _max_cachefile_age=0)
    assert cmk_base.modes.check_mk.mode_check_discovery("ds-test-host1") == 1
    assert _counter_run == 2


def test_mode_check_discovery_cached(test_cfg, monkeypatch, mock):
    _patch_data_source_run(monkeypatch, _max_cachefile_age=120, _use_outdated_cache_file=True, _may_use_cache_file=True)

    try:
        cmk_base.modes.check_mk.option_cache()
        assert cmk_base.modes.check_mk.mode_check_discovery("ds-test-host1") == 1
        assert _counter_run == 2
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk_base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_discover_all_hosts(test_cfg, monkeypatch, mock):
    _patch_data_source_run(monkeypatch, _may_use_cache_file=True, _max_cachefile_age=120)
    cmk_base.modes.check_mk.mode_discover({"discover": 1}, [])
    assert _counter_run == len(config.all_active_realhosts())*2


def test_mode_discover_explicit_hosts(test_cfg, monkeypatch):
    # TODO: Is it correct that no cache is used here?
    _patch_data_source_run(monkeypatch, _max_cachefile_age=0)
    cmk_base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert _counter_run == 2


def test_mode_discover_explicit_hosts_cache(test_cfg, monkeypatch):
    try:
        _patch_data_source_run(monkeypatch, _max_cachefile_age=120, _may_use_cache_file=True, _use_outdated_cache_file=True)
        cmk_base.modes.check_mk.option_cache()
        cmk_base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
        assert _counter_run == 2
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk_base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_discover_explicit_hosts_no_cache(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch, _no_cache=True, _max_cachefile_age=0)
    cmk_base.modes.check_mk.option_no_cache() # --no-cache
    cmk_base.modes.check_mk.mode_discover({"discover": 1}, ["ds-test-host1"])
    assert _counter_run == 2


def test_mode_check_explicit_host(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch)
    cmk_base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert _counter_run == 2


def test_mode_check_explicit_host_cache(test_cfg, monkeypatch):
    try:
        _patch_data_source_run(monkeypatch, _may_use_cache_file=True, _use_outdated_cache_file=True)
        cmk_base.modes.check_mk.option_cache()
        cmk_base.modes.check_mk.mode_check({}, ["ds-test-host1"])
        assert _counter_run == 2
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk_base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_check_explicit_host_no_cache(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch, _no_cache=True, _max_cachefile_age=0)
    cmk_base.modes.check_mk.option_no_cache() # --no-cache
    cmk_base.modes.check_mk.mode_check({}, ["ds-test-host1"])
    assert _counter_run == 2


def test_mode_dump_agent_explicit_host(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch)
    cmk_base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert _counter_run == 2


def test_mode_dump_agent_explicit_host_cache(test_cfg, monkeypatch):
    try:
        _patch_data_source_run(monkeypatch, _may_use_cache_file=True, _use_outdated_cache_file=True)
        cmk_base.modes.check_mk.option_cache()
        cmk_base.modes.check_mk.mode_dump_agent("ds-test-host1")
        assert _counter_run == 2
    finally:
        # TODO: Can't the mode clean this up on it's own?
        cmk_base.data_sources.abstract.DataSource.set_use_outdated_cache_file(False)


def test_mode_dump_agent_explicit_host_no_cache(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch, _no_cache=True, _max_cachefile_age=0)
    cmk_base.modes.check_mk.option_no_cache() # --no-cache
    cmk_base.modes.check_mk.mode_dump_agent("ds-test-host1")
    assert _counter_run == 2


@pytest.mark.parametrize(("scan"), [
    ("@noscan", {"_do_snmp_scan": False, "_may_use_cache_file": True, "_max_cachefile_age": 120}),
    ("@scan", {"_do_snmp_scan": True, "_may_use_cache_file": False, "_max_cachefile_age": 0}),
])
@pytest.mark.parametrize(("raise_errors"), [
    ("@raiseerrors", {"_on_error": "raise"}),
    (None, {"_on_error": "ignore"}),
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

    cmk_base.automations.check_mk.AutomationTryDiscovery().execute(args)
    assert _counter_run == 2


@pytest.mark.parametrize(("raise_errors"), [
    ("@raiseerrors", {"_on_error": "raise"}),
    (None, {"_on_error": "ignore"}),
])
@pytest.mark.parametrize(("scan"), [
    (None, {"_do_snmp_scan": False}),
    ("@scan", {"_do_snmp_scan": True}),
])
@pytest.mark.parametrize(("cache"), [
    ("@cache", {"_max_cachefile_age": 120}), # TODO: Why not _may_use_cache_file=True? like try-discovery
    (None, {"_max_cachefile_age": 0}),
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

    args += [ "fixall", "ds-test-host1" ]

    _patch_data_source_run(monkeypatch, **kwargs)

    cmk_base.automations.check_mk.AutomationDiscovery().execute(args)
    assert _counter_run == 2


def test_automation_diag_host_caching(test_cfg, monkeypatch):
    _patch_data_source_run(monkeypatch)

    args = ["ds-test-host1", "agent", "127.0.0.1", None, 6557, 10, 5, 5, None ]
    cmk_base.automations.check_mk.AutomationDiagHost().execute(args)
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

#
# UNIT TESTS
#

# Automatically refresh caches for each test
@pytest.fixture(scope="function")
def clear_config_caches(monkeypatch):
    import cmk_base
    import cmk_base.caching
    monkeypatch.setattr(cmk_base, "config_cache", cmk_base.caching.CacheManager())
    monkeypatch.setattr(cmk_base, "runtime_cache", cmk_base.caching.CacheManager())


def test_data_sources_of_hosts(clear_config_caches, monkeypatch):
    hosts = [
        # Configs from 1.4
        ("agent-host-14", {
            "tags": "lan|cmk-agent|ip-v4|tcp|ip-v4-only|prod",
            "sources": ['TCPDataSource', 'PiggyBackDataSource'],
        }),
        ("ds-host-14", {
            "tags": "lan|cmk-agent|ip-v4|tcp|ip-v4-only|prod",
            "sources": ['DSProgramDataSource', 'PiggyBackDataSource'],
        }),
        ("special-host-14", {
            "tags": "lan|cmk-agent|ip-v4|tcp|ip-v4-only|prod",
            "sources": ['SpecialAgentDataSource', 'PiggyBackDataSource'],
        }),
        ("ping-host-14", {
            "tags": "lan|ip-v4|ping|ip-v4-only|prod",
            "sources": ['PiggyBackDataSource'],
        }),
        ("snmp-host-14", {
            "tags": "lan|ip-v4|snmp|snmp-only|ip-v4-only|prod",
            "sources": ['SNMPDataSource', 'PiggyBackDataSource'],
        }),
        ("snmpv1-host-14", {
            "tags": "lan|ip-v4|snmp|snmp-v1|ip-v4-only|prod",
            "sources": ['SNMPDataSource', 'PiggyBackDataSource'],
        }),
        ("dual-host-14", {
            "tags": "lan|ip-v4|snmp|tcp|ip-v4-only|prod|snmp-tcp",
            "sources": ['TCPDataSource', 'SNMPDataSource', 'PiggyBackDataSource'],
        }),
        # From current WATO
        ("agent-host", {
            "tags": "lan|ip-v4|cmk-agent|no-snmp|tcp|ip-v4-only|prod",
            "sources": ['TCPDataSource', 'PiggyBackDataSource'],
        }),
        ("ping-host", {
            "tags": "lan|ip-v4|ping|no-snmp|ip-v4-only|no-agent|prod",
            "sources": ['PiggyBackDataSource'],
        }),
        ("snmp-host", {
            "tags": "lan|ip-v4|snmp|snmp-v2|ip-v4-only|no-agent|prod",
            "sources": ['SNMPDataSource', 'PiggyBackDataSource'],
        }),
        ("snmpv1-host", {
            "tags": "lan|ip-v4|snmp|snmp-v1|ip-v4-only|no-agent|prod",
            "sources": ['SNMPDataSource', 'PiggyBackDataSource'],
        }),
        ("dual-host", {
            "tags": "lan|ip-v4|cmk-agent|snmp|snmp-v2|ip-v4-only|tcp|prod",
            "sources": ['TCPDataSource', 'SNMPDataSource', 'PiggyBackDataSource'],
        }),
        ("all-agents-host", {
            "tags": "lan|all-agents|ip-v4|no-snmp|tcp|ip-v4-only|prod",
            "sources": ['DSProgramDataSource', 'SpecialAgentDataSource', 'PiggyBackDataSource'],
        }),
        ("all-special-host", {
            "tags": "lan|ip-v4|no-snmp|tcp|ip-v4-only|special-agents|prod",
            "sources": ['SpecialAgentDataSource', 'PiggyBackDataSource'],
        }),
    ]

    import cmk_base.data_sources
    import cmk_base.config as config

    all_hosts = [ ("%s|%s" % (name, h["tags"])) for name, h in hosts ]
    monkeypatch.setattr(config, "all_hosts", all_hosts)

    monkeypatch.setattr(config, "datasource_programs", [
        ( 'echo 1', [], ['ds-host-14', 'all-agents-host', 'all-special-host' ], {} ),
    ])

    monkeypatch.setitem(config.special_agents, "jolokia", [
        ( {}, [], ['special-host-14', 'all-agents-host', 'all-special-host', ], {} ),
    ])

    config.collect_hosttags()

    for hostname, host_attrs in hosts:
        sources = cmk_base.data_sources.DataSources(hostname, "127.0.0.1")
        source_names = [ s.__class__.__name__ for s in sources.get_data_sources() ]
        assert host_attrs["sources"] == source_names, \
            "Wrong sources for %s" % hostname
