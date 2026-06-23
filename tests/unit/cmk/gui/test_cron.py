#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui import cron


def test_registered_jobs() -> None:
    expected = [
        "execute_inventory_cleanup_job",
        "execute_housekeeping_job",
        "rebuild_folder_lookup_cache",
        "execute_userdb_job",
        "execute_user_messages_spool_job",
        "execute_user_profile_cleanup_job",
        "execute_network_scan_job",
        "execute_activation_cleanup_job",
        "execute_sync_remote_sites",
        "execute_host_removal_job",
        "cleanup_topology_layouts",
        "execute_autodiscovery",
        "execute_deprecation_tests_and_notify_users",
        "cleanup_crash_reports",
    ]

    found_jobs = sorted([f.name for f in cron.cron_job_registry.values()])
    assert found_jobs == sorted(expected)
