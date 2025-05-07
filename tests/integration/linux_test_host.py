#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import get_standard_linux_agent_output


def create_linux_test_host(request: pytest.FixtureRequest, site: Site, hostname: str) -> None:
    def get_data_source_cache_files(name: str) -> list[str]:
        p = site.execute(
            ["ls", f"tmp/check_mk/data_source_cache/*/{name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        output = p.communicate()[0].strip()
        if not output:
            return []
        assert isinstance(output, str)
        return output.split(" ")

    def finalizer() -> None:
        site.openapi.hosts.delete(hostname)
        site.activate_changes_and_wait_for_core_reload()

        for path in [
            "var/check_mk/agent_output/%s" % hostname,
            "etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname,
            "tmp/check_mk/status_data/%s" % hostname,
            "tmp/check_mk/status_data/%s.gz" % hostname,
            "var/check_mk/inventory/%s" % hostname,
            "var/check_mk/inventory/%s.gz" % hostname,
            "var/check_mk/autochecks/%s.mk" % hostname,
            "tmp/check_mk/counters/%s" % hostname,
            "tmp/check_mk/cache/%s" % hostname,
        ] + get_data_source_cache_files(hostname):
            if site.file_exists(path):
                site.delete_file(path)

    request.addfinalizer(finalizer)

    site.openapi.hosts.create(hostname, attributes={"ipaddress": "127.0.0.1"})

    site.write_file(
        "etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname,
        f"datasource_programs.append({{'condition': {{'hostname': ['{hostname}']}}, 'value': 'cat ~/var/check_mk/agent_output/<HOST>'}})\n",
    )

    site.makedirs("var/check_mk/agent_output/")
    site.write_file("var/check_mk/agent_output/%s" % hostname, get_standard_linux_agent_output())
