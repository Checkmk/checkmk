#!/usr/bin/env python
# These tests verify the behaviour of the Check_MK base methods
# that do the actual checking/discovery/inventory work. Especially
# the default caching and handling of global options affecting the
# caching is checked

import pytest
from testlib import web, repo_path

import cmk_base.config as config
import cmk_base.modes

@pytest.fixture(scope="module")
def test_cfg(web, site):
    print "Applying default config"
    web.add_host("ds-test-host1", attributes={
        "ipaddress": "127.0.0.1",
    })
    web.add_host("ds-test-host2", attributes={
        "ipaddress": "127.0.0.1",
    })

    site.write_file("etc/check_mk/conf.d/ds-test-host.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ALL_HOSTS))\n")

    site.makedirs("var/check_mk/agent_output/")
    site.write_file("var/check_mk/agent_output/ds-test-host1",
            file("%s/tests/data/linux-agent-output" % repo_path()).read())
    site.write_file("var/check_mk/agent_output/ds-test-host2",
            file("%s/tests/data/linux-agent-output" % repo_path()).read())

    web.activate_changes()

    import cmk.debug
    cmk.debug.enable()

    config.load()
    yield None

    #
    # Cleanup code
    #
    print "Cleaning up test config"

    site.delete_dir("var/check_mk/agent_output")
    site.delete_file("etc/check_mk/conf.d/ds-test-host.mk")

    web.delete_host("ds-test-host1")
    web.delete_host("ds-test-host2")

    web.activate_changes()


# Globale Optionen:
# --cache
# --no-cache
# --no-tcp
# --usewalk
# --force

# TODO: Use force
# TODO: With hostnames and without
def test_mode_inventory_set_caching(test_cfg, mocker):
    use_cachefile_patcher = mocker.patch("cmk_base.data_sources.abstract.DataSource.set_use_cachefile")
    use_persisted_sections_patcher = mocker.patch("cmk_base.data_sources.abstract.CheckMKAgentDataSource.use_outdated_persisted_sections")

    # When called without hosts, it uses all hosts and defaults to using the data source cache
    cmk_base.modes.check_mk.mode_inventory([], [])
    use_cachefile_patcher.assert_called_once_with()
    use_persisted_sections_patcher.assert_not_called()

    # When called with an explicit list of hosts the cache is not used by default
    cmk_base.modes.check_mk.mode_inventory([], ["ds-test-host1"])
    use_cachefile_patcher.assert_not_called()
    use_persisted_sections_patcher.assert_not_called()

    cmk_base.modes.check_mk.mode_inventory(["force"], ["ds-test-host1"])
    use_cachefile_patcher.assert_not_called()
    use_persisted_sections_patcher.assert_called()

# mode_inventory()
# mode_inventory_as_check(options, hostname):
# mode_discover_marked_hosts():
# mode_check_discovery(*args):
# mode_discover(options, args):
# mode_check(options, args):
# dump host
#
# automation:
# AutomationTryDiscovery
# AutomationDiscovery
# AutomationDiagHost
#
# Keepalive check
# Keepalive discovery

