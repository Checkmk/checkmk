#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import subprocess

import pytest

from cmk.checkengine.discovery import AutochecksSerializer
from tests.system.singlesite.cmk.base.automation_helper_restart import (
    restart_automation_helper_and_wait_until_reachable,
)
from tests.system.singlesite.linux_test_host import create_linux_test_host
from tests.testlib.system.site import Site

_PLUGIN_SRC = "test_plugins/check_variables_plugin/agent_based/test_check_3.py"
_PLUGIN_DST = (
    "local/lib/python3/cmk_addons/plugins/check_variables_test/agent_based/test_check_3.py"
)


# Test whether or not factory settings and checkgroup parameters work
def test_check_default_parameters(request: pytest.FixtureRequest, site: Site) -> None:
    host_name = "check-variables-test-host"

    create_linux_test_host(request, site, host_name)
    site.write_file(f"var/check_mk/agent_output/{host_name}", "<<<test_check_3>>>\n1 2\n")

    def cleanup() -> None:
        if site.file_exists("etc/check_mk/conf.d/test_check_3.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_3.mk")
        # the plug-in is gone by now, make the automation helper forget about it
        restart_automation_helper_and_wait_until_reachable(site)

    request.addfinalizer(cleanup)

    with site.copy_file(_PLUGIN_SRC, _PLUGIN_DST):
        site.activate_changes_and_wait_for_core_reload()
        # discovery runs in the automation helper, which only loads plug-ins on startup
        restart_automation_helper_and_wait_until_reachable(site)
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)

        # Verify that the discovery worked as expected
        entries = AutochecksSerializer().deserialize(
            site.read_file(f"var/check_mk/autochecks/{host_name}.mk").encode("utf-8")
        )
        assert str(entries[0].check_plugin_name) == "test_check_3"
        assert entries[0].item is None
        assert entries[0].parameters == {}
        assert entries[0].service_labels == {}

        # Now execute the check function to verify the default parameters are applied.
        # The per-service results are only logged with -vv, and they go to stderr.
        p = site.execute(["cmk", "-nvv", host_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert "[agent] Success" in stdout, stdout
        assert "params={'param1': 123}" in stderr, stderr
        assert p.returncode == 0

        # And now overwrite the setting in the config
        site.write_file(
            "etc/check_mk/conf.d/test_check_3.mk",
            """
checkgroup_parameters.setdefault('asd', [])

checkgroup_parameters['asd'] = [
    {'condition': {}, 'options': {}, 'value': {'param2': 'xxx'}},
] + checkgroup_parameters['asd']
""",
        )

        # And execute the check again to check for the parameters
        p = site.execute(["cmk", "-nvv", host_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert "[agent] Success" in stdout, stdout
        assert "'param1': 123" in stderr, stderr
        assert "'param2': 'xxx'" in stderr, stderr
        assert p.returncode == 0
