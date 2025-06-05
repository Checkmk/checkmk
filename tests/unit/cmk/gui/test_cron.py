#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.version as cmk_version

import cmk.gui.cron as cron


def test_registered_jobs() -> None:

    expected = [
        "cmk.gui.inventory.execute_inventory_housekeeping_job",
        "cmk.gui.background_job.execute_housekeeping_job",
        "cmk.gui.watolib.hosts_and_folders.rebuild_folder_lookup_cache",
        "cmk.gui.userdb.execute_userdb_job",
        "cmk.gui.userdb.execute_user_profile_cleanup_job",
        "cmk.gui.watolib.network_scan.execute_network_scan_job",
        "cmk.gui.watolib.activate_changes.execute_activation_cleanup_background_job",
        "cmk.gui.plugins.wato.remote_audit_logs.execute_get_remote_audit_logs",
        "cmk.gui.watolib.automatic_host_removal.execute_host_removal_background_job",
        "cmk.gui.node_visualization.cleanup_topology_layouts",
    ]

    if not cmk_version.is_raw_edition():
        expected += [
            "cmk.gui.cce.plugins.wato.agent_registration.background_jobs.execute_host_registration_background_job",
            "cmk.gui.cce.plugins.wato.agent_registration.background_jobs.execute_discover_registered_hosts_background_job",
            "cmk.gui.cee.reporting.cleanup_stored_reports",
            "cmk.gui.cee.reporting.do_scheduled_reports",
            "cmk.gui.cee.ntop.connector.ntop_instance_check",
            "cmk.gui.cee.plugins.wato.licensing.background_jobs.execute_licensing_online_verification_background_job",
            "cmk.gui.watolib.host_label_sync.execute_host_label_sync_job",
            "cmk.gui.cee.userdb.saml2.config.replace_builtin_signature_cert",
            "cmk.gui.cee.plugins.wato.agent_bakery._cronjobs.execute_signing_key_validation_job",
        ]

    found_jobs = sorted([f"{f.__module__}.{f.__name__}" for f in cron.multisite_cronjobs])
    assert found_jobs == sorted(expected)
