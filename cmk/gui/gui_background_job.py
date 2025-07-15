#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal, override

import cmk.ccc.plugin_registry
from cmk.ccc.exceptions import MKGeneralException

import cmk.utils.render

from cmk.gui import background_job as background_job
from cmk.gui import log
from cmk.gui.background_job import BackgroundJob, BackgroundStatusSnapshot
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.permissions import (
    Permission,
    PermissionRegistry,
    PermissionSection,
    PermissionSectionRegistry,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri_contextless


def register(
    permission_section_registry: PermissionSectionRegistry, permission_registry: PermissionRegistry
) -> None:
    permission_section_registry.register(PERMISSION_SECTION_BACKGROUND_JOBS)
    permission_registry.register(PermissionManageJobs)
    permission_registry.register(PermissionStopJobs)
    permission_registry.register(PermissionDeleteJobs)
    permission_registry.register(PermissionSeeForeignJobs)
    permission_registry.register(PermissionStopForeignJobs)
    permission_registry.register(PermissionDeleteForeignJobs)


PERMISSION_SECTION_BACKGROUND_JOBS = PermissionSection(
    name="background_jobs",
    title=_("Background jobs"),
)


PermissionManageJobs = Permission(
    section=PERMISSION_SECTION_BACKGROUND_JOBS,
    name="manage_jobs",
    title=_l("Manage background jobs"),
    description=_l("Allows you to see the job overview page."),
    defaults=["admin"],
)

PermissionStopJobs = Permission(
    section=PERMISSION_SECTION_BACKGROUND_JOBS,
    name="stop_jobs",
    title=_l("Stop background jobs"),
    description=_l(
        "Configures the permission to stop background jobs. Note: some jobs cannot be stopped."
    ),
    defaults=["user", "admin"],
)

PermissionDeleteJobs = Permission(
    section=PERMISSION_SECTION_BACKGROUND_JOBS,
    name="delete_jobs",
    title=_l("Delete background jobs"),
    description=_l(
        "Configures the permission to delete background jobs. Note: some jobs cannot be deleted."
    ),
    defaults=["user", "admin"],
)

PermissionSeeForeignJobs = Permission(
    section=PERMISSION_SECTION_BACKGROUND_JOBS,
    name="see_foreign_jobs",
    title=_l("See foreign background jobs"),
    description=_l("Allows you to see jobs of other users."),
    defaults=["admin"],
)

PermissionStopForeignJobs = Permission(
    section=PERMISSION_SECTION_BACKGROUND_JOBS,
    name="stop_foreign_jobs",
    title=_l("Stop foreign background jobs"),
    description=_l("Allows you to stop jobs of other users. Note: some jobs cannot be stopped."),
    defaults=["admin"],
)

PermissionDeleteForeignJobs = Permission(
    section=PERMISSION_SECTION_BACKGROUND_JOBS,
    name="delete_foreign_jobs",
    title=_l("Delete foreign background jobs"),
    description=_l("Allows you to delete jobs of other users. Note: some jobs cannot be deleted"),
    defaults=["admin"],
)


@dataclass
class JobInfo:
    status: background_job.JobStatusSpec
    may_stop: bool
    may_delete: bool


class GUIBackgroundJobManager(background_job.BackgroundJobManager):
    def __init__(self) -> None:
        super().__init__(logger=log.logger.getChild("background-job.manager"))

    @override
    def get_running_job_ids(
        self, job_class: type[background_job.BackgroundJob]
    ) -> list[background_job.JobId]:
        job_ids = super().get_running_job_ids(job_class)
        return self._filter_available_jobs(job_ids)

    @override
    def get_all_job_ids(
        self, job_class: type[background_job.BackgroundJob] | None = None
    ) -> list[background_job.JobId]:
        job_ids = super().get_all_job_ids(job_class)
        return self._filter_available_jobs(job_ids)

    def _filter_available_jobs(
        self, job_ids: Sequence[background_job.JobId]
    ) -> list[background_job.JobId]:
        visible_jobs = []
        for job_id in job_ids:
            try:
                job = BackgroundJob(job_id)
                if job.is_available():
                    visible_jobs.append(job_id)
            except Exception as e:
                self._logger.error(f"Exception parsing background job {job_id}: {e}")
                continue
        return visible_jobs

    def show_status_of_job_classes(
        self, job_classes: Iterable[type[BackgroundJob]], job_details_back_url: str
    ) -> None:
        job_class_infos: dict[
            type[BackgroundJob],
            dict[background_job.JobId, JobInfo],
        ] = {}
        for job_class in job_classes:
            all_job_ids = self.get_all_job_ids(job_class)
            if not all_job_ids:
                continue  # Skip job classes without current jobs
            job_class_infos[job_class] = self._get_job_infos(all_job_ids)

        JobRenderer.show_job_class_infos(job_class_infos, job_details_back_url)

    def show_job_details_from_snapshot(self, job_snapshot: BackgroundStatusSnapshot) -> None:
        if not job_snapshot.exists:
            raise MKGeneralException(
                "Background job with id <i>%s</i> not found" % job_snapshot.job_id
            )
        JobRenderer.show_job_details(
            job_snapshot.job_id, job_snapshot.status, job_snapshot.may_stop, job_snapshot.may_delete
        )

    def _get_job_infos(
        self, jobs: Sequence[background_job.JobId]
    ) -> dict[background_job.JobId, JobInfo]:
        all_jobs = {}
        for job_id in jobs:
            try:
                job = BackgroundJob(job_id)
                job_status = job.get_status()
                is_active = job.is_active()
            except Exception as e:
                self._logger.error(f"Exception parsing background job {job_id}: {str(e)}")
                continue

            all_jobs[job_id] = JobInfo(
                status=job_status,
                may_stop=is_active and job.may_stop(),
                may_delete=job.may_delete(),
            )
        return all_jobs


# .
#   .--Rendering-----------------------------------------------------------.
#   |            ____                _           _                         |
#   |           |  _ \ ___ _ __   __| | ___ _ __(_)_ __   __ _             |
#   |           | |_) / _ \ '_ \ / _` |/ _ \ '__| | '_ \ / _` |            |
#   |           |  _ <  __/ | | | (_| |  __/ |  | | | | | (_| |            |
#   |           |_| \_\___|_| |_|\__,_|\___|_|  |_|_| |_|\__, |            |
#   |                                                    |___/             |
#   +----------------------------------------------------------------------+


class JobRenderer:
    @classmethod
    def show_job_details(
        cls,
        job_id: background_job.JobId,
        job_status: background_job.JobStatusSpec,
        may_stop: bool,
        may_delete: bool,
    ) -> None:
        """Renders the complete job details in a single table with left headers"""
        html.open_table(class_=["data", "headerleft", "job_details"])

        # Static info
        for left, right in [
            (_("ID"), job_id),
            (_("Title"), job_status.title),
            (_("Started"), cmk.utils.render.date_and_time(job_status.started)),
            (_("Owner"), job_status.user),
        ]:
            html.open_tr()
            html.th(left)
            html.td(right)
            html.close_tr()

        # Actions
        html.open_tr()
        html.th(_("Actions"))
        html.open_td()
        if may_stop:
            html.icon_button(
                make_confirm_delete_link(
                    url=makeactionuri(
                        request, transactions, [(ActionHandler.stop_job_var, job_id)]
                    ),
                    title=_("Stop job"),
                    suffix=job_status.title,
                    message=_("ID: %s") % job_id,
                    confirm_button=_("Stop"),
                    cancel_button=_("Cancel"),
                ),
                _("Stop this job"),
                "disable_test",
            )
        if may_delete:
            html.icon_button(
                make_confirm_delete_link(
                    url=makeactionuri(
                        request, transactions, [(ActionHandler.delete_job_var, job_id)]
                    ),
                    title=_("Delete job"),
                    suffix=job_status.title,
                    message=_("ID: %s") % job_id,
                ),
                _("Delete this job"),
                "delete",
            )
        html.close_td()
        html.close_tr()

        # Job state
        html.open_tr()
        html.th(_("State"))
        html.td(job_status.state, css=cls.get_css_for_jobstate(job_status.state))
        html.close_tr()

        if job_status.state == background_job.JobStatusStates.EXCEPTION:
            html.open_tr()
            html.th(_("Acknowledged by"))
            html.td(job_status.acknowledged_by or "")
            html.close_tr()

        # Dynamic data
        loginfo = job_status.loginfo
        runtime_info = cmk.utils.render.timespan(job_status.duration)
        if (
            job_status.state == background_job.JobStatusStates.RUNNING
            and (estimated_duration := job_status.estimated_duration) is not None
        ):
            runtime_info += " ({}: {})".format(
                _("estimated duration"),
                cmk.utils.render.timespan(estimated_duration),
            )
        for left, right in [
            (_("Runtime"), runtime_info),
            (_("Thread ID"), str(job_status.pid) or ""),
            (_("Result"), "<br>".join(loginfo["JobResult"])),
        ]:
            if right is None:
                continue
            html.open_tr()
            html.th(left)
            html.td(HTML.without_escaping(right))
            html.close_tr()

        # Exceptions
        exceptions = list(loginfo["JobException"])
        if exceptions:
            html.open_tr()
            html.th(_("Exceptions"))
            html.open_td()
            if exceptions:
                exceptions.append(
                    _("More information can be found in %s") % job_status.logfile_path
                )
            html.open_div(class_="log_output", id_="exception_log")
            html.pre("\n".join(exceptions))
            html.close_div()
            html.close_td()
            html.close_tr()

        # Progress Update
        html.open_tr()
        html.th(_("Progress info"))
        html.open_td()
        html.open_div(class_="log_output", style="height: 400px;", id_="progress_log")
        html.pre(HTML.without_escaping("\n").join(loginfo["JobProgressUpdate"]))
        html.pre(HTML.without_escaping("\n".join(loginfo["JobResult"])))
        html.close_div()
        html.close_td()
        html.close_tr()

        html.close_table()

    @classmethod
    def _get_extra_info(cls, job_status: background_job.JobStatusSpec) -> str:
        return " (%s)" % job_status.title

    @classmethod
    def show_job_class_infos(
        cls,
        job_class_infos: dict[
            type[BackgroundJob],
            dict[background_job.JobId, JobInfo],
        ],
        job_details_back_url: str,
    ) -> None:
        """Renders all jobs from the job_class_infos in a single multi-table"""
        html.open_table(css="job_table data")
        for job_class, jobs_info in sorted(job_class_infos.items(), key=lambda x: x[0].gui_title()):
            html.open_tr()
            html.open_td(colspan=len(cls.get_headers()))
            html.h3(job_class.gui_title())
            html.close_td()
            html.close_tr()

            if not jobs_info:
                html.open_tr()
                html.open_td(colspan=len(cls.get_headers()))
                html.div(_("No entries"), css="info")
                html.close_td()
                html.close_tr()
                continue

            cls.show_job_row_headers()
            odd: Literal["odd", "even"] = "even"
            for job_id, job_info in sorted(
                jobs_info.items(), key=lambda x: x[1].status.started, reverse=True
            ):
                cls.render_job_row(job_id, job_info, odd, job_details_back_url)
                odd = "even" if odd == "odd" else "odd"

    @classmethod
    def show_job_row_headers(cls) -> None:
        html.open_tr()
        for header in cls.get_headers():
            html.th(header)
        html.close_tr()

    @classmethod
    def get_headers(cls) -> list[str]:
        return [
            _("Actions"),
            _("Job ID"),
            _("Job Title"),
            _("State"),
            _("Started"),
            _("Owner"),
            _("Thread ID"),
            _("Runtime"),
            _("Last progress info"),
            _("Results"),
        ]

    @classmethod
    def render_job_row(
        cls,
        job_id: background_job.JobId,
        job_info: JobInfo,
        odd: Literal["odd", "even"],
        job_details_back_url: str,
    ) -> None:
        job_status = job_info.status

        html.open_tr(css="data %s0" % odd)

        # Actions
        html.open_td(css="job_actions")
        if job_info.may_stop:
            html.icon_button(
                makeactionuri(request, transactions, [(ActionHandler.stop_job_var, job_id)]),
                _("Stop this job"),
                "disable_test",
            )
        if job_info.may_delete:
            html.icon_button(
                makeactionuri(request, transactions, [(ActionHandler.delete_job_var, job_id)]),
                _("Delete this job"),
                "delete",
            )
        html.close_td()

        # Job ID
        html.open_td(css="job_id")
        uri = makeuri_contextless(
            request,
            [
                ("mode", "background_job_details"),
                ("back_url", job_details_back_url),
                ("job_id", job_id),
            ],
            filename="wato.py",
        )
        html.a(job_id, href=uri)
        html.close_td()

        html.td(job_status.title, css="job_title")
        html.td(
            HTMLWriter.render_span(job_status.state),
            css=cls.get_css_for_jobstate(job_status.state),
        )
        html.td(cmk.utils.render.date_and_time(job_status.started), css="job_started")
        html.td(job_status.user or _("Internal user"), css="job_owner")
        html.td(job_status.pid or "", css="job_pid")
        html.td(cmk.utils.render.timespan(job_status.duration), css="job_runtime")

        # Progress info
        loginfo = job_status.loginfo
        if loginfo:
            if job_status.state == background_job.JobStatusStates.EXCEPTION:
                html.td(
                    HTMLWriter.render_br().join(loginfo["JobException"]), css="job_last_progress"
                )
            else:
                progress_text = ""
                if loginfo["JobProgressUpdate"]:
                    progress_text += "%s" % loginfo["JobProgressUpdate"][-1]
                html.td(HTML.without_escaping(progress_text), css="job_last_progress")

            html.td(
                HTML.without_escaping("<br>".join(loginfo["JobResult"])),
                css="job_result",
            )
        else:
            html.td("", css="job_last_progress")
            html.td("", css="job_result")

    @classmethod
    def get_css_for_jobstate(cls, job_state: str) -> str:
        job_css_map = {
            background_job.JobStatusStates.INITIALIZED: "state statep",
            background_job.JobStatusStates.RUNNING: "state job_running",
            background_job.JobStatusStates.EXCEPTION: "state state2",
            background_job.JobStatusStates.STOPPED: "state state1",  # same css as warn
            background_job.JobStatusStates.FINISHED: "state state0",
        }
        return job_css_map.get(job_state, "")


# .
#   .--Actions-------------------------------------------------------------.
#   |                     _        _   _                                   |
#   |                    / \   ___| |_(_) ___  _ __  ___                   |
#   |                   / _ \ / __| __| |/ _ \| '_ \/ __|                  |
#   |                  / ___ \ (__| |_| | (_) | | | \__ \                  |
#   |                 /_/   \_\___|\__|_|\___/|_| |_|___/                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class ActionHandler:
    stop_job_var = "_stop_job"
    delete_job_var = "_delete_job"
    acknowledge_job_var = "_acknowledge_job"

    def __init__(self, breadcrumb: Breadcrumb) -> None:
        super().__init__()
        self._breadcrumb = breadcrumb
        self._did_acknowledge_job = False
        self._did_stop_job = False
        self._did_delete_job = False

    def confirm_dialog_opened(self) -> bool:
        for action_var in [self.stop_job_var, self.delete_job_var]:
            if request.has_var(action_var):
                return True
        return False

    def handle_actions(self) -> bool:
        if request.var(self.acknowledge_job_var):
            self.acknowledge_job()
            return True
        if request.var(self.stop_job_var):
            self.stop_job()
            return True
        if request.var(self.delete_job_var):
            self.delete_job()
            return True
        return False

    def did_acknowledge_job(self) -> bool:
        return self._did_acknowledge_job

    def did_stop_job(self) -> bool:
        return self._did_stop_job

    def did_delete_job(self) -> bool:
        return self._did_delete_job

    def acknowledge_job(self) -> None:
        job_id = request.get_ascii_input_mandatory(self.acknowledge_job_var)
        job = BackgroundJob(job_id)
        if not job.is_available():
            return

        self._did_acknowledge_job = True
        job.acknowledge(user.id)

    def stop_job(self) -> None:
        job_id = request.get_ascii_input_mandatory(self.stop_job_var)
        job = BackgroundJob(job_id)
        if not job.is_available():
            return

        if not job.is_active():
            html.show_message(_("No longer able to stop job. Background job just finished."))
            return

        if job.may_stop():
            job.stop()
            self._did_stop_job = True
            html.show_message(_("Background job has been stopped"))

    def delete_job(self) -> None:
        job_id = request.get_ascii_input_mandatory(self.delete_job_var)
        job = BackgroundJob(job_id)
        if not job.is_available():
            return

        if job.may_delete():
            job.delete()
            self._did_delete_job = True
            html.show_message(_("Background job has been deleted"))
