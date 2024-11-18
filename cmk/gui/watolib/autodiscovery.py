#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import omd_site

import cmk.utils.paths
from cmk.utils.auto_queue import AutoQueue

from cmk.checkengine.discovery import DiscoveryResult as SingleHostDiscoveryResult

from cmk.gui.background_job import BackgroundJob, BackgroundProcessInterface, InitialStatusArgs
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.changes import add_service_change
from cmk.gui.watolib.check_mk_automations import autodiscovery
from cmk.gui.watolib.hosts_and_folders import Host


class AutodiscoveryBackgroundJob(BackgroundJob):
    job_prefix = "autodiscovery"

    @classmethod
    def gui_title(cls) -> str:
        return _("Autodiscovery")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)
        self.site_id = omd_site()

    @staticmethod
    def _get_discovery_message_text(
        hostname: str, discovery_result: SingleHostDiscoveryResult
    ) -> str:
        return _(
            "Did service discovery on host %s: %d added, %d removed, %d kept, "
            "%d total services and %d host labels added, %d host labels total"
        ) % (
            hostname,
            discovery_result.self_new,
            discovery_result.self_removed,
            discovery_result.self_kept,
            discovery_result.self_total,
            discovery_result.self_new_host_labels,
            discovery_result.self_total_host_labels,
        )

    def do_execute(self, job_interface: BackgroundProcessInterface) -> None:
        with job_interface.gui_context():
            self._execute(job_interface)

    def _execute(self, job_interface: BackgroundProcessInterface) -> None:
        result = autodiscovery(self.site_id)

        if not result.hosts:
            job_interface.send_result_message(_("No hosts to be discovered"))
            return

        for hostname, discovery_result in result.hosts.items():
            host = Host.host(hostname)
            if host is None:
                continue

            message = self._get_discovery_message_text(hostname, discovery_result)

            if result.changes_activated:
                log_audit(
                    action="autodiscovery",
                    message=message,
                    object_ref=host.object_ref(),
                    user_id=user.id,
                    diff_text=discovery_result.diff_text,
                )
            else:
                add_service_change(
                    "autodiscovery",
                    message,
                    host.object_ref(),
                    self.site_id,
                    diff_text=discovery_result.diff_text,
                )

        if result.changes_activated:
            log_audit("activate-changes", "Started activation of site %s" % self.site_id)

        job_interface.send_result_message(_("Successfully discovered hosts"))


def execute_autodiscovery() -> None:
    # Only execute the job in case there is some work to do. The directory was so far internal to
    # "autodiscovery" automation which is implemented in cmk.base.automations.checkm_mk. But since
    # this condition saves us a lot of overhead and this function is part of the feature, it seems
    # to be acceptable to do this.
    if len(AutoQueue(cmk.utils.paths.autodiscovery_dir)) == 0:
        logger.debug("No hosts to be discovered")
        return

    job = AutodiscoveryBackgroundJob()
    if job.is_active():
        logger.debug("Another 'autodiscovery' job is already running: Skipping this time.")
        return

    job.start(
        job.do_execute,
        InitialStatusArgs(
            title=job.gui_title(),
            lock_wato=False,
            stoppable=False,
            user=str(user.id) if user.id else None,
        ),
    )
