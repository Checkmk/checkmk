#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.cron import cron_job_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_jobs() -> None:
    assert sorted(cron_job_registry) == [
        "cleanup_crash_reports",
        "cleanup_topology_layouts",
        "compile_bi_aggregations",
        "consolidate_crash_reports",
        "execute_activation_cleanup_job",
        "execute_autodiscovery",
        "execute_deprecation_tests_and_notify_users",
        "execute_host_removal_job",
        "execute_housekeeping_job",
        "execute_inventory_cleanup_job",
        "execute_ldap_quarantine_cleanup_job",
        "execute_network_scan_job",
        "execute_sync_remote_sites",
        "execute_user_messages_spool_job",
        "execute_user_profile_cleanup_job",
        "execute_userdb_job",
        "rebuild_folder_lookup_cache",
    ]
