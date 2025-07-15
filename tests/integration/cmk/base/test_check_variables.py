#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

import pytest

from tests.integration.linux_test_host import create_linux_test_host

from tests.testlib.site import Site
from tests.testlib.version import CMKEdition

from cmk.utils import paths

from cmk.checkengine.discovery._autochecks import _AutochecksSerializer


# Test whether or not factory settings and checkgroup parameters work
@pytest.mark.skipif(
    CMKEdition.edition_from_path(paths.omd_root).is_raw_edition(), reason="flaky on raw edition"
)
def test_check_default_parameters(request: pytest.FixtureRequest, site: Site) -> None:
    host_name = "check-variables-test-host"

    create_linux_test_host(request, site, host_name)
    site.write_file(f"var/check_mk/agent_output/{host_name}", "<<<test_check_3>>>\n1 2\n")

    test_check_path = "local/share/check_mk/checks/test_check_3"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_3.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_3.mk")

        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.write_file(
        test_check_path,
        """

def inventory(info):
    yield None, {}

def check(item, params, info):
    yield 0, "OK - %r" % (params, )

check_info["test_check_3"] = LegacyCheckDefinition(
    check_function=check,
    discovery_function=inventory,
    service_name="Testcheck 3",
    check_ruleset_name="asd",
    check_default_parameters={"param1": 123},
)
""",
    )

    site.activate_changes_and_wait_for_core_reload()
    site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)

    # Verify that the discovery worked as expected
    entries = _AutochecksSerializer().deserialize(
        site.read_file(f"var/check_mk/autochecks/{host_name}.mk").encode("utf-8")
    )
    assert str(entries[0].check_plugin_name) == "test_check_3"
    assert entries[0].item is None
    assert entries[0].parameters == {}
    assert entries[0].service_labels == {}

    # Now execute the check function to verify the variable is available
    p = site.execute(["cmk", "-nv", host_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert "OK - {'param1': 123}\n" in stdout, stdout
    assert stderr == ""
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
    p = site.execute(["cmk", "-nv", host_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert "'param1': 123" in stdout
    assert "'param2': 'xxx'" in stdout
    assert stderr == ""
    assert p.returncode == 0
