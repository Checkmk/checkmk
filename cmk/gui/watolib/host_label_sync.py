#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Synchronize discovered host labels from remote site to central site"""

from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Tuple, Any
from multiprocessing.pool import ThreadPool

from livestatus import SiteId, SiteConfiguration

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.labels import (get_updated_host_label_files, save_updated_host_label_files,
                              UpdatedHostLabels)

import cmk.gui.log as log
from cmk.gui.log import logger
import cmk.gui.pages
import cmk.gui.config as config
import cmk.gui.background_job as background_job
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.watolib.automation_commands import AutomationCommand, automation_command_registry
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.globals import html
from cmk.gui.i18n import _


@dataclass
class SiteResult:
    site_id: SiteId
    success: bool
    error: str
    updated_host_labels: UpdatedHostLabels


@dataclass
class DiscoveredHostLabelSyncResponse:
    updated_host_labels: UpdatedHostLabels


def execute_host_label_sync_job():
    """This function is called by the GUI cron job once a minute.
    Errors are logged to var/log/web.log."""
    if not config.has_wato_slave_sites():
        return

    job = DiscoveredHostLabelSyncJob()
    if job.is_active():
        logger.debug("Another synchronization job is already running: Skipping this sync")
        return

    job.set_function(job.do_sync)
    job.start()


@gui_background_job.job_registry.register
class DiscoveredHostLabelSyncJob(gui_background_job.GUIBackgroundJob):
    """This job synchronizes the discovered host labels from remote sites to the central site

    Currently they are only needed for the agent bakery, but may be used in other places in the
    future.
    """
    job_prefix = "discovered_host_label_sync"

    @classmethod
    def gui_title(cls) -> str:
        return _("Discovered host label synchronization")

    def __init__(self) -> None:
        super().__init__(
            job_id=self.job_prefix,
            title=self.gui_title(),
            stoppable=False,
        )

    def do_sync(self, job_interface: background_job.BackgroundProcessInterface):
        job_interface.send_progress_update(_("Synchronization started..."))
        self._execute_sync()
        job_interface.send_result_message(_("The synchronization finished."))

    def _execute_sync(self) -> None:
        newest_host_labels = self._load_newest_host_labels_per_site()

        with ThreadPool(20) as pool:
            results = pool.map(self._execute_site_sync,
                               [(site_id, site_spec, newest_host_labels.get(site_id, 0.0))
                                for site_id, site_spec in config.wato_slave_sites().items()])

        for site_result in results:
            if not site_result.updated_host_labels:
                continue

            newest_host_labels[site_result.site_id] = max(
                [e[1] for e in site_result.updated_host_labels])
            save_updated_host_label_files(site_result.updated_host_labels)

        self._save_newest_host_labels_per_site(newest_host_labels)

    def _execute_site_sync(self, args: Tuple[SiteId, SiteConfiguration, float]) -> SiteResult:
        """Executes the sync with a site. Is executed in a dedicated subprocess (One per site)"""
        try:
            site_id, site_spec, newest_host_labels = args
            logger.debug(_("[%s] Starting sync for site"), site_id)

            # Reinitialize logging targets
            log.init_logging()  # NOTE: We run in a subprocess!

            result = DiscoveredHostLabelSyncResponse(
                **do_remote_automation(site_spec,
                                       "discovered-host-label-sync", [("newest_host_labels",
                                                                       newest_host_labels)],
                                       timeout=html.request.request_timeout - 10))

            logger.debug(_("[%s] Finished sync for site"), site_id)
            return SiteResult(
                site_id=site_id,
                success=True,
                error="",
                updated_host_labels=result.updated_host_labels,
            )
        except Exception as e:
            logger.error('Exception (%s, discovered_host_label_sync)', site_id, exc_info=True)
            return SiteResult(
                site_id=site_id,
                success=False,
                error=str(e),
                updated_host_labels=[],
            )

    @staticmethod
    def newest_host_labels_per_site_path() -> Path:
        return Path(cmk.utils.paths.var_dir) / "wato" / "newest_host_labels_per_site.mk"

    def _load_newest_host_labels_per_site(self) -> Dict[SiteId, float]:
        return store.load_object_from_file(
            DiscoveredHostLabelSyncJob.newest_host_labels_per_site_path(), default={})

    def _save_newest_host_labels_per_site(self, newest_host_labels: Dict[SiteId, float]) -> None:
        store.save_object_to_file(DiscoveredHostLabelSyncJob.newest_host_labels_per_site_path(),
                                  newest_host_labels)


@automation_command_registry.register
class AutomationDiscoveredHostLabelSync(AutomationCommand):
    """Called by DiscoveredHostLabelSyncJob._execute_site_sync to perform the sync with a remote site"""
    def command_name(self) -> str:
        return "discovered-host-label-sync"

    def get_request(self) -> float:
        return html.request.get_float_input_mandatory("newest_host_labels")

    def execute(self, request: float) -> Dict[str, Any]:
        return asdict(
            DiscoveredHostLabelSyncResponse(get_updated_host_label_files(newer_than=request)))
