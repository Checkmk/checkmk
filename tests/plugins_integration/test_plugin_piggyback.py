#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import re
import time

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import get_services_with_status, write_file

from tests.plugins_integration.checks import (
    dump_path_site,
    get_host_names,
    get_piggyback_hosts,
    read_cmk_dump,
    read_disk_dump,
    setup_source_host_piggyback,
    wait_for_dcd_pend_changes,
)

logger = logging.getLogger(__name__)


def _read_piggyback_hosts_from_dump(dump: str) -> set[str]:
    piggyback_hosts: set[str] = set()
    pattern = r"<<<<(.*?)>>>>"
    matches = re.findall(pattern, dump)
    piggyback_hosts.update(matches)
    piggyback_hosts.discard("")  # '<<<<>>>>' pattern will match an empty string
    return piggyback_hosts


def _rm_piggyback_host_from_dump(dump: str, host_name: str) -> str:
    host_start = f"<<<<{host_name}>>>>"
    host_end = "<<<<>>>>"
    max_count = 20
    counter = 0

    while counter < max_count:
        logger.info(
            "Removing PB host %s from the agent dump. Count: %s/%s", host_name, counter, max_count
        )
        # Find the index of the start marker
        start_index = dump.find(host_start)
        if start_index == -1:  # host not found
            break

        # Find the index of the end marker after the start marker
        end_index = dump.find(host_end, start_index + len(host_start))
        assert end_index != -1, "Host block end marker not found"

        # Remove the substring between the markers
        dump = dump[:start_index] + dump[end_index + len(host_end) :]
        counter += 1

    return dump


def _wait_for_pb_host_deletion(site: Site, source_host_name: str, pb_host_name: str) -> None:
    max_count = 30
    counter = 0
    while pb_host_name in get_piggyback_hosts(site, source_host_name) and counter < max_count:
        logger.info(
            "Waiting for PB host %s to be removed from the site. Count: %s/%s",
            pb_host_name,
            counter,
            max_count,
        )
        time.sleep(5)
        counter += 1

    assert pb_host_name not in get_piggyback_hosts(
        site, source_host_name
    ), f"Host {pb_host_name} was not removed from the site."


@pytest.mark.xfail(reason="Test is failing. Temporary xfailing it to investigate the problem.")
@pytest.mark.parametrize("source_host_name", get_host_names(piggyback=True))
def test_plugin_piggyback(
    test_site_piggyback: Site,
    source_host_name: str,
) -> None:
    with setup_source_host_piggyback(test_site_piggyback, source_host_name):
        disk_dump = read_disk_dump(source_host_name, piggyback=True)
        cmk_dump = read_cmk_dump(source_host_name, test_site_piggyback, "agent")
        assert disk_dump == cmk_dump != "", "Raw data mismatch!"

        piggyback_hostnames = get_piggyback_hosts(test_site_piggyback, source_host_name)
        assert set(piggyback_hostnames) == _read_piggyback_hosts_from_dump(disk_dump)

        for hostname in piggyback_hostnames:
            host_services = test_site_piggyback.get_host_services(hostname)
            ok_services = get_services_with_status(host_services, 0)
            not_ok_services = [service for service in host_services if service not in ok_services]
            err_msg = (
                f"The following services are not in state 0: {not_ok_services} "
                f"(Details: {[host_services[s] for s in not_ok_services]})"
            )
            assert len(host_services) == len(ok_services), err_msg

        # test removal of piggyback host
        pb_host_to_rm = piggyback_hostnames[0]
        updated_dump = _rm_piggyback_host_from_dump(disk_dump, pb_host_to_rm)
        write_file(test_site_piggyback.path(dump_path_site / source_host_name), updated_dump)

        assert pb_host_to_rm not in _read_piggyback_hosts_from_dump(
            updated_dump
        ), f"Host {pb_host_to_rm} was not removed from the agent dump."

        _wait_for_pb_host_deletion(test_site_piggyback, source_host_name, pb_host_to_rm)
        wait_for_dcd_pend_changes(test_site_piggyback)
