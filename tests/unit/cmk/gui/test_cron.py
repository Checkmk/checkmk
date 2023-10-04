#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.version as cmk_version

import cmk.gui.cron as cron


def test_registered_jobs() -> None:
    expected = [
        "cmk.gui.inventory.execute_inventory_housekeeping_job",
        "cmk.gui.background_job._manager.execute_housekeeping_job",
        "cmk.gui.watolib.hosts_and_folders.rebuild_folder_lookup_cache",
        "cmk.gui.userdb._user_sync.execute_userdb_job",
        "cmk.gui.userdb._user_profile_cleanup.execute_user_profile_cleanup_job",
        "cmk.gui.watolib.network_scan.execute_network_scan_job",
        "cmk.gui.watolib.activate_changes.execute_activation_cleanup_background_job",
        "cmk.gui.watolib._sync_remote_sites.execute_sync_remote_sites",
        "cmk.gui.watolib.automatic_host_removal.execute_host_removal_background_job",
        "cmk.gui.node_visualization.cleanup_topology_layouts",
        "cmk.gui.watolib.autodiscovery.execute_autodiscovery",
    ]

    if cmk_version.edition() is not cmk_version.Edition.CRE:
        expected += [
            "cmk.gui.cce.agent_registration._background_jobs.execute_host_registration_background_job",
            "cmk.gui.cce.agent_registration._background_jobs.execute_discover_registered_hosts_background_job",
            "cmk.gui.cee.reporting._stored_reports.cleanup_stored_reports",
            "cmk.gui.cee.reporting._scheduler.do_scheduled_reports",
            "cmk.gui.cee.ntop.connector.ntop_instance_check",
            "cmk.gui.cee.licensing._background_jobs.execute_licensing_online_verification_background_job",
            "cmk.gui.watolib.host_label_sync.execute_host_label_sync_job",
            "cmk.gui.cee.userdb.saml2.config.replace_builtin_signature_cert",
        ]

    found_jobs = sorted([f"{f.__module__}.{f.__name__}" for f in cron.multisite_cronjobs])
    assert found_jobs == sorted(expected)
