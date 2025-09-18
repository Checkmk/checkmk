#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import textwrap

import pytest

from tests.plugins_integration.checks import config, dump_path_site, process_check_output
from tests.testlib.agent_dumps import (
    get_dump_names,
    read_cmk_dump,
    read_disk_dump,
    read_piggyback_hosts_from_dump,
)
from tests.testlib.agent_hosts import piggyback_host_from_dump_file
from tests.testlib.dcd import execute_dcd_cycle
from tests.testlib.site import Site
from tests.testlib.utils import write_file

logger = logging.getLogger(__name__)


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


@pytest.mark.parametrize(
    "source_host_name", get_dump_names(config.dump_dir_integration / "piggyback")
)
def test_plugin_piggyback(
    test_site_piggyback: Site,
    source_host_name: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    dump_path_repo = config.dump_dir_integration / "piggyback"
    response_path_repo = config.response_dir_integration / "piggyback"
    diffs_path = tmp_path_factory.mktemp("diffs")
    output_path = tmp_path_factory.mktemp("output")

    with piggyback_host_from_dump_file(
        test_site_piggyback,
        source_host_name,
        source_dir=dump_path_repo,
        target_dir=dump_path_site,
    ):
        disk_dump = read_disk_dump(source_host_name, dump_path_repo)
        cmk_dump = read_cmk_dump(source_host_name, test_site_piggyback, "agent")
        assert disk_dump == cmk_dump != "", "Raw data mismatch!"

        piggyback_hostnames = test_site_piggyback.openapi.hosts.get_all_names([source_host_name])
        piggyback_hostnames_from_dump = read_piggyback_hosts_from_dump(disk_dump)
        pb_hosts_symmetric_diff = set(piggyback_hostnames).symmetric_difference(
            piggyback_hostnames_from_dump
        )
        assert not pb_hosts_symmetric_diff, (
            f"PB hosts found within the site: {piggyback_hostnames}\n"
            f"PB hosts found in the dump: {piggyback_hostnames_from_dump}\n"
            f"Symmetric difference: {pb_hosts_symmetric_diff}"
        )

        for hostname in piggyback_hostnames:
            diffing_checks = process_check_output(
                site=test_site_piggyback,
                host_name=hostname,
                response_path=response_path_repo / f"{hostname}.json",
                diff_dir=diffs_path,
                output_dir=output_path,
            )

            err_msg = f"Check output mismatch for host {hostname}:\n" + "".join(
                [textwrap.dedent(f"{check}:\n" + diffing_checks[check]) for check in diffing_checks]
            )
            assert not diffing_checks, err_msg

        # test removal of piggyback host
        pb_host_to_rm = piggyback_hostnames[0]
        updated_dump = _rm_piggyback_host_from_dump(disk_dump, pb_host_to_rm)
        write_file(test_site_piggyback.path(dump_path_site / source_host_name), updated_dump)

        assert pb_host_to_rm not in (pb_hosts := read_piggyback_hosts_from_dump(updated_dump)), (
            f"Host {pb_host_to_rm} was not removed from the agent dump."
        )
        execute_dcd_cycle(test_site_piggyback, expected_pb_hosts=len(pb_hosts))
        assert pb_host_to_rm not in test_site_piggyback.openapi.hosts.get_all_names(), (
            f"Host {pb_host_to_rm} was not removed from the site."
        )
