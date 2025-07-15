#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import omd_site

import cmk.utils.paths
from cmk.utils.auto_queue import AutoQueue

from cmk.checkengine.discovery import DiscoveryReport as SingleHostDiscoveryResult

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    NoArgs,
    simple_job_target,
)
from cmk.gui.config import active_config, Config
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.changes import add_service_change
from cmk.gui.watolib.check_mk_automations import autodiscovery
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    generate_hosts_to_update_settings,
)
from cmk.gui.watolib.config_domain_name import (
    CORE as CORE_DOMAIN,
)
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
            "Discovery on host %s: %d services (%d added, %d changed, %d removed, %d kept)"
            " and %d host labels (%d added, %d changed, %d removed, %d kept)"
        ) % (
            hostname,
            discovery_result.services.total,
            discovery_result.services.new,
            discovery_result.services.changed,
            discovery_result.services.removed,
            discovery_result.services.kept,
            discovery_result.host_labels.total,
            discovery_result.host_labels.new,
            discovery_result.host_labels.changed,
            discovery_result.host_labels.removed,
            discovery_result.host_labels.kept,
        )

    def execute(self, job_interface: BackgroundProcessInterface, *, debug: bool) -> None:
        result = autodiscovery(debug=debug)

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
                    use_git=active_config.wato_use_git,
                )
            else:
                add_service_change(
                    action_name="autodiscovery",
                    text=message,
                    user_id=user.id,
                    object_ref=host.object_ref(),
                    domains=[config_domain_registry[CORE_DOMAIN]],
                    domain_settings={CORE_DOMAIN: generate_hosts_to_update_settings([host.name()])},
                    site_id=self.site_id,
                    diff_text=discovery_result.diff_text,
                    use_git=active_config.wato_use_git,
                )

        if result.changes_activated:
            log_audit(
                action="activate-changes",
                message="Started activation of site %s" % self.site_id,
                user_id=user.id,
                use_git=active_config.wato_use_git,
            )

        job_interface.send_result_message(_("Successfully discovered hosts"))


def execute_autodiscovery(config: Config) -> None:
    # Only execute the job in case there is some work to do. The directory was so far internal to
    # "autodiscovery" automation which is implemented in cmk.base.automations.checkm_mk. But since
    # this condition saves us a lot of overhead and this function is part of the feature, it seems
    # to be acceptable to do this.
    if len(AutoQueue(cmk.utils.paths.autodiscovery_dir)) == 0:
        logger.debug("No hosts to be discovered")
        return

    job = AutodiscoveryBackgroundJob()
    if (
        result := job.start(
            simple_job_target(autodiscovery_job_entry_point),
            InitialStatusArgs(
                title=job.gui_title(),
                lock_wato=False,
                stoppable=False,
                user=str(user.id) if user.id else None,
            ),
        )
    ).is_error():
        logger.error(str(result))


def autodiscovery_job_entry_point(job_interface: BackgroundProcessInterface, args: NoArgs) -> None:
    with job_interface.gui_context():
        AutodiscoveryBackgroundJob().execute(job_interface, debug=active_config.debug)
