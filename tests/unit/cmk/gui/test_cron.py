#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.ccc.version as cmk_version

from cmk.utils import paths

from cmk.gui import cron


def test_registered_jobs() -> None:
    expected = [
        "execute_inventory_housekeeping_job",
        "execute_housekeeping_job",
        "rebuild_folder_lookup_cache",
        "execute_userdb_job",
        "execute_user_profile_cleanup_job",
        "execute_network_scan_job",
        "execute_activation_cleanup_job",
        "execute_sync_remote_sites",
        "execute_host_removal_job",
        "cleanup_topology_layouts",
        "execute_autodiscovery",
        "execute_deprecation_tests_and_notify_users",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected += [
            "execute_host_registration_job",
            "execute_discover_registered_hosts_job",
            "cleanup_stored_reports",
            "do_scheduled_reports",
            "ntop_instance_check",
            "execute_licensing_online_verification_background_job",
            "execute_host_label_sync_job",
            "replace_builtin_signature_cert",
            "execute_signing_key_validation_job",
        ]

    found_jobs = sorted([f.name for f in cron.cron_job_registry.values()])
    assert found_jobs == sorted(expected)
