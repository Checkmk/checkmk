#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback

import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.log import logger

from cmk.gui.plugins.wato import (
    main_module_registry,
    MainModule,
    WatoMode,
    mode_registry,
)


@main_module_registry.register
class MainModuleBackgroundJobs(MainModule):
    @property
    def mode_or_url(self):
        return "background_jobs_overview"

    @property
    def title(self):
        return _("Background jobs")

    @property
    def icon(self):
        return "background_jobs"

    @property
    def permission(self):
        return "background_jobs.manage_jobs"

    @property
    def description(self):
        return _("Manage longer running tasks in the Check_MK GUI")

    @property
    def sort_index(self):
        return 90


@mode_registry.register
class ModeBackgroundJobsOverview(WatoMode):
    @classmethod
    def name(cls):
        return "background_jobs_overview"

    @classmethod
    def permissions(cls):
        return ["background_jobs.manage_jobs"]

    def title(self):
        return _("Background jobs overview")

    def page(self):
        job_manager = gui_background_job.GUIBackgroundJobManager()

        back_url = html.makeuri_contextless([("mode", "background_jobs_overview")])
        job_manager.show_status_of_job_classes(gui_background_job.job_registry.values(),
                                               job_details_back_url=back_url)

        if any(
                job_manager.get_running_job_ids(c)
                for c in gui_background_job.job_registry.values()):
            html.immediate_browser_redirect(0.8, "")

    def action(self):
        action_handler = gui_background_job.ActionHandler()
        action_handler.handle_actions()


@mode_registry.register
class ModeBackgroundJobDetails(WatoMode):
    @classmethod
    def name(cls):
        return "background_job_details"

    @classmethod
    def permissions(cls):
        return []

    def title(self):
        return _("Background job details")

    def buttons(self):
        if self._back_url():
            html.context_button(_("Back"), self._back_url(), "back")

    def _back_url(self):
        return html.get_url_input("back_url", deflt="")

    def page(self):
        job_id = html.request.var("job_id")

        job = gui_background_job.GUIBackgroundJob(job_id)
        if not job.exists():
            html.show_message(_("Background job info is not available"))
            return

        try:
            # Race condition, the job might get deleted during snapshot generation
            job_snapshot = job.get_status_snapshot()
        except Exception:
            html.show_message(_("Background job info is not available"))
            logger.error(traceback.format_exc())
            return

        job_manager = gui_background_job.GUIBackgroundJobManager()
        job_manager.show_job_details_from_snapshot(job_snapshot)
        if job_snapshot.is_active():
            html.immediate_browser_redirect(1, "")

    def action(self):
        action_handler = gui_background_job.ActionHandler()
        action_handler.handle_actions()
        if action_handler.did_delete_job():
            if self._back_url():
                raise HTTPRedirect(self._back_url())
            return "background_jobs_overview"
