#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Type
from six import ensure_str

import cmk
import cmk.utils.plugin_registry
from cmk.utils.exceptions import MKGeneralException
import cmk.utils.render

import cmk.gui.i18n
import cmk.gui.sites as sites
import cmk.gui.config as config
import cmk.gui.log as log
import cmk.gui.background_job as background_job
from cmk.gui.i18n import _, _l
from cmk.gui.globals import g, html
from cmk.gui.htmllib import HTML
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
    permission_registry,
    Permission,
)


@permission_section_registry.register
class PermissionSectionBackgroundJobs(PermissionSection):
    @property
    def name(self):
        return "background_jobs"

    @property
    def title(self):
        return _("Background jobs")


permission_registry.register(
    Permission(
        section=PermissionSectionBackgroundJobs,
        name="manage_jobs",
        title=_l("Manage background jobs"),
        description=_l("Allows you to see the job overview page."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=PermissionSectionBackgroundJobs,
        name="stop_jobs",
        title=_l("Stop background jobs"),
        description=_l(
            "Configures the permission to stop background jobs. Note: some jobs cannot be stopped."
        ),
        defaults=["user", "admin"],
    ))

permission_registry.register(
    Permission(
        section=PermissionSectionBackgroundJobs,
        name="delete_jobs",
        title=_l("Delete background jobs"),
        description=_l(
            "Configures the permission to delete background jobs. Note: some jobs cannot be deleted."
        ),
        defaults=["user", "admin"],
    ))

permission_registry.register(
    Permission(
        section=PermissionSectionBackgroundJobs,
        name="see_foreign_jobs",
        title=_l("See foreign background jobs"),
        description=_l("Allows you to see jobs of other users."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=PermissionSectionBackgroundJobs,
        name="stop_foreign_jobs",
        title=_l("Stop foreign background jobs"),
        description=_l(
            "Allows you to stop jobs of other users. Note: some jobs cannot be stopped."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=PermissionSectionBackgroundJobs,
        name="delete_foreign_jobs",
        title=_l("Delete foreign background jobs"),
        description=_l(
            "Allows you to delete jobs of other users. Note: some jobs cannot be deleted"),
        defaults=["admin"],
    ))


class GUIBackgroundProcess(background_job.BackgroundProcess):
    def initialize_environment(self):
        # setup logging
        log.init_logging()  # NOTE: We run in a subprocess!
        self._logger = log.logger.getChild("background-job")
        self._log_path_hint = _("More information can be found in ~/var/log/web.log")

        # Disable html request timeout
        if html:
            html.disable_request_timeout()

        # Close livestatus connections inherited from the parent process
        if g:
            sites.disconnect()

        super(GUIBackgroundProcess, self).initialize_environment()


# These functions here are included in a frozen snapshot of a background job
# Restrictions for newly added functions: no function arguments, only getters
class GUIBackgroundJobSnapshottedFunctions(background_job.BackgroundJob):
    def has_exception(self):
        return self.get_status().get("state") == background_job.JobStatusStates.EXCEPTION

    def acknowledged_by(self):
        return self.get_status().get("acknowledged_by")

    def is_available(self):
        return self.exists() and self.is_visible()

    def is_deletable(self):
        return self.get_status().get("deletable", True)

    def is_visible(self):
        if config.user.may("background_jobs.see_foreign_jobs"):
            return True
        return config.user.id == self.get_status().get("user")

    def may_stop(self):
        if not self.is_stoppable():
            return False

        if not config.user.may("background_jobs.stop_jobs"):
            return False

        if self.is_foreign() and not config.user.may("background_jobs.stop_foreign_jobs"):
            return False

        if not self.is_active():
            return False

        return True

    def may_delete(self):
        if not self.is_deletable():
            return False

        if not self.is_stoppable() and self.is_active():
            return False

        if not config.user.may("background_jobs.delete_jobs"):
            return False

        if self.is_foreign() and not config.user.may("background_jobs.delete_foreign_jobs"):
            return False

        return True

    def is_foreign(self):
        return self.get_status().get("user") != config.user.id

    # FIXME: There is some arcane metaprogramming Kung Fu going on in
    # GUIBackgroundStatusSnapshot which needs the methods *in this class*,
    # although they are actually totally useless here.
    def is_active(self):  # pylint: disable=useless-super-delegation
        return super(GUIBackgroundJobSnapshottedFunctions, self).is_active()

    def exists(self):  # pylint: disable=useless-super-delegation
        return super(GUIBackgroundJobSnapshottedFunctions, self).exists()

    def get_job_id(self):  # pylint: disable=useless-super-delegation
        return super(GUIBackgroundJobSnapshottedFunctions, self).get_job_id()

    def get_title(self):  # pylint: disable=useless-super-delegation
        return super(GUIBackgroundJobSnapshottedFunctions, self).get_title()


class GUIBackgroundJob(GUIBackgroundJobSnapshottedFunctions):
    _background_process_class = GUIBackgroundProcess

    def __init__(self, job_id, **kwargs):
        logger = log.logger.getChild("background-job")
        kwargs["user"] = config.user.id
        kwargs["logfile_path"] = "~/var/log/web.log"
        # Deletable is currently a GUI only feature, not known in background_job
        self._deletable = kwargs.get("deletable", True)

        super(GUIBackgroundJob, self).__init__(job_id, logger=logger, **kwargs)

    @classmethod
    def gui_title(cls) -> str:
        # FIXME: This method cannot be made abstract since GUIBackgroundJob is
        # instantiated in various places.
        raise NotImplementedError()

    def get_status_snapshot(self):
        return GUIBackgroundStatusSnapshot(self)

    def acknowledge(self, user_id):
        self.update_status({"acknowledged_by": user_id})

    def detail_url(self):
        """Returns the URL that displays the job detail page"""
        return html.makeuri_contextless(
            [
                ("mode", "background_job_details"),
                ("job_id", self.get_job_id()),
                ("back_url", self._back_url()),
            ],
            filename="wato.py",
        )

    def _back_url(self):
        """Returns either None or the URL that the job detail page may be link back"""
        return None


class GUIBackgroundJobRegistry(cmk.utils.plugin_registry.Registry[Type[GUIBackgroundJob]]):
    def plugin_name(self, instance):
        return instance.__name__


job_registry = GUIBackgroundJobRegistry()


# GUI pages are built in several phases, and each face can take a non-trivial
# amount of time. Nevertheless, it is crucial to render a consistent state of
# the background job in question. The class below provides such a status
# snapshot for the job given to the constructor.
#
# TODO: BackgroundJob should provide an explicit status object, which we can use
# here without any metaprogramming Kung Fu and arcane inheritance hierarchies.
class GUIBackgroundStatusSnapshot:
    def __init__(self, job):
        super(GUIBackgroundStatusSnapshot, self).__init__()
        self._job_status = job.get_status()
        self._logger = job._logger.getChild("snapshot")

        for name, value in GUIBackgroundJobSnapshottedFunctions.__dict__.items():
            if hasattr(value, "__call__"):
                self._job_status[name] = getattr(job, name)()

    def get_status_as_dict(self):
        return {self.get_job_id(): self._job_status}

    def __getattr__(self, name):
        if name not in self._job_status:
            raise MKGeneralException(
                _("The function %s is not in the snapshotted functions.") % name)
        return lambda: self._job_status[name]


class GUIBackgroundJobManager(background_job.BackgroundJobManager):
    def __init__(self):
        super(GUIBackgroundJobManager,
              self).__init__(logger=log.logger.getChild("background-job.manager"))

    def get_running_job_ids(self, job_class):
        job_ids = super(GUIBackgroundJobManager, self).get_running_job_ids(job_class)
        return self._filter_available_jobs(job_ids)

    def get_all_job_ids(self, job_class):
        job_ids = super(GUIBackgroundJobManager, self).get_all_job_ids(job_class)
        return self._filter_available_jobs(job_ids)

    def _filter_available_jobs(self, job_ids):
        visible_jobs = []
        for job_id in job_ids:
            try:
                job = GUIBackgroundJob(job_id)
                if job.is_available():
                    visible_jobs.append(job_id)
            except Exception as e:
                self._logger.error("Exception parsing background job %s: %s" % (job_id, e))
                continue
        return visible_jobs

    def show_status_of_job_classes(self, job_classes, **kwargs):
        job_class_infos = {}
        for job_class in job_classes:
            all_job_ids = self.get_all_job_ids(job_class)
            if not all_job_ids:
                continue  # Skip job classes without current jobs
            job_class_infos[job_class] = self._get_job_infos(all_job_ids)

        JobRenderer.show_job_class_infos(job_class_infos, **kwargs)

    def get_status_all_jobs(self, job_class):
        all_job_ids = self.get_all_job_ids(job_class)
        return self._get_job_infos(all_job_ids)

    def show_job_details(self, job_id=None, job_snapshot=None):
        job_info = self._get_job_infos([job_id])
        if not job_info:
            raise MKGeneralException("Background job with id <i>%s</i> not found" % job_id)

        job_id, job_status = list(job_info.items())[0]
        JobRenderer.show_job_details(job_id, job_status)

    def show_job_details_from_snapshot(self, job_snapshot):
        if job_snapshot.exists():
            job_info = job_snapshot.get_status_as_dict()
            job_id, job_status = list(job_info.items())[0]
            JobRenderer.show_job_details(job_id, job_status)
        else:
            raise MKGeneralException("Background job with id <i>%s</i> not found" %
                                     job_snapshot.get_job_id())

    def _get_job_infos(self, jobs):
        all_jobs = {}
        for job_id in jobs:
            try:
                job = GUIBackgroundJob(job_id)
                job_status = job.get_status()
                is_active = job.is_active()
            except Exception as e:
                self._logger.error("Exception parsing background job %s: %s" % (job_id, str(e)))
                continue

            if is_active and job.may_stop():
                job_status["may_stop"] = True

            if job.may_delete():
                job_status["may_delete"] = True
            all_jobs[job_id] = job_status
        return all_jobs


#.
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
    def show_job_details(cls, job_id, job_status):
        """Renders the complete job details in a single table with left headers"""
        html.open_table(class_=["data", "headerleft", "job_details"])

        # Static info
        for left, right in [
            (_("ID"), job_id),
            (_("Title"), job_status.get("title", "")),
            (_("Started"), cmk.utils.render.date_and_time(job_status["started"])),
            (_("Owner"), job_status.get("user", "")),
        ]:
            html.open_tr()
            html.th(left)
            html.td(right)
            html.close_tr()

        # Actions
        html.open_tr()
        html.th(_("Actions"))
        html.open_td()
        if job_status.get("may_stop"):
            html.icon_button(
                html.makeactionuri([(ActionHandler.stop_job_var, job_id)]),
                _("Stop this job"),
                "disable_test",
            )
        if job_status.get("may_delete"):
            html.icon_button(
                html.makeactionuri([(ActionHandler.delete_job_var, job_id)]),
                _("Delete this job"),
                "delete",
            )
        html.close_td()
        html.close_tr()

        # Job state
        html.open_tr()
        html.th(_("State"))
        html.td(job_status["state"], css=cls.get_css_for_jobstate(job_status["state"]))
        html.close_tr()

        if job_status["state"] == background_job.JobStatusStates.EXCEPTION:
            html.open_tr()
            html.th(_("Acknowledged by"))
            html.td(job_status.get("acknowledged_by", ""))
            html.close_tr()

        # Dynamic data
        loginfo = job_status.get("loginfo")
        runtime_info = ensure_str(cmk.utils.render.timespan(job_status.get("duration", 0)))
        if job_status["state"] == background_job.JobStatusStates.RUNNING \
            and job_status.get("estimated_duration") is not None:
            runtime_info += u" (%s: %s)" % (
                _("estimated duration"),
                ensure_str(cmk.utils.render.timespan(job_status["estimated_duration"])))
        for left, right in [
            (_("Runtime"), runtime_info),
            (_("PID"), job_status["pid"] or ""),
            (_("Result"), "<br>".join(loginfo["JobResult"])),
        ]:
            if right is None:
                continue
            html.open_tr()
            html.th(left)
            html.td(HTML(right))
            html.close_tr()

        # Exceptions
        exceptions = loginfo["JobException"]
        if exceptions:
            html.open_tr()
            html.th(_("Exceptions"))
            html.open_td()
            if exceptions and "logfile_path" in job_status:
                exceptions.append(
                    _("More information can be found in %s") % job_status["logfile_path"])
            html.open_div(class_="log_output", id_="exception_log")
            html.pre("\n".join(exceptions))
            html.close_div()
            html.close_td()
            html.close_tr()

        # Progress Update
        html.open_tr()
        html.th(_("Progress Info"))
        html.open_td()
        html.open_div(class_="log_output", style="height: 400px;", id_="progress_log")
        html.pre(HTML("\n").join(loginfo["JobProgressUpdate"]))
        html.close_div()
        html.close_td()
        html.close_tr()

        html.close_table()
        html.javascript(
            "var log = document.getElementById('progress_log'); log.scrollTop = log.scrollHeight;")

    @classmethod
    def show_job_class_infos(cls, job_class_infos, **kwargs):
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
            odd = "even"
            for job_id, job_status in sorted(jobs_info.items(),
                                             key=lambda x: x[1]["started"],
                                             reverse=True):
                cls.render_job_row(job_id, job_status, odd, **kwargs)
                odd = "even" if odd == "odd" else "odd"

    @classmethod
    def show_job_row_headers(cls):
        html.open_tr()
        for header in cls.get_headers():
            html.th(header)
        html.close_tr()

    @classmethod
    def get_headers(cls):
        return [
            _("Actions"),
            _("Job ID"),
            _("Job Title"),
            _("State"),
            _("Started"),
            _("Owner"),
            _("PID"),
            _("Runtime"),
            _("Last progress info"),
            _("Results")
        ]

    @classmethod
    def render_job_row(cls, job_id, job_status, odd, job_details_back_url=None):
        html.open_tr(css="data %s0" % odd)

        # Actions
        html.open_td(css="job_actions")
        if job_status.get("may_stop"):
            html.icon_button(html.makeactionuri([(ActionHandler.stop_job_var, job_id)]),
                             _("Stop this job"), "disable_test")
        if job_status.get("may_delete"):
            html.icon_button(html.makeactionuri([(ActionHandler.delete_job_var, job_id)]),
                             _("Delete this job"), "delete")
        html.close_td()

        # Job ID
        html.open_td(css="job_id")
        uri = html.makeuri_contextless([("mode", "background_job_details"),
                                        ("back_url", job_details_back_url), ("job_id", job_id)],
                                       filename="wato.py")
        html.a(job_id, href=uri)
        html.close_td()

        # Title
        html.td(job_status.get("title", _("Background Job")), css="job_title")

        # State
        html.td(job_status["state"], css=cls.get_css_for_jobstate(job_status["state"]))

        # Started
        html.td(cmk.utils.render.date_and_time(job_status["started"]), css="job_started")

        # Owner
        html.td(job_status.get("user", _("Unknown user")), css="job_owner")

        # PID
        html.td(job_status["pid"] or "", css="job_pid")

        # Druation
        html.td(cmk.utils.render.timespan(job_status.get("duration", 0)), css="job_runtime")

        # Progress info
        loginfo = job_status.get("loginfo")
        if loginfo:
            if job_status.get("state") == background_job.JobStatusStates.EXCEPTION:
                html.td(HTML("<br>".join(loginfo["JobException"])), css="job_last_progress")
            else:
                progress_text = ""
                if loginfo["JobProgressUpdate"]:
                    progress_text += "%s" % loginfo["JobProgressUpdate"][-1]
                html.td(HTML(progress_text), css="job_last_progress")

            html.td(HTML("<br>".join(loginfo["JobResult"])), css="job_result")
        else:
            html.td("", css="job_last_progress")
            html.td("", css="job_result")

    @classmethod
    def get_css_for_jobstate(cls, job_state):
        job_css_map = {
            background_job.JobStatusStates.INITIALIZED: "job_state job_initialized",
            background_job.JobStatusStates.RUNNING: "job_state job_running",
            background_job.JobStatusStates.EXCEPTION: "job_state job_exception",
            background_job.JobStatusStates.STOPPED: "job_state job_exception",  # same css as exception
            background_job.JobStatusStates.FINISHED: "job_state job_finished"
        }
        return job_css_map.get(job_state, "")


#.
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

    def __init__(self, breadcrumb: Breadcrumb):
        super(ActionHandler, self).__init__()
        self._breadcrumb = breadcrumb
        self._did_acknowledge_job = False
        self._did_stop_job = False
        self._did_delete_job = False

    def confirm_dialog_opened(self):
        for action_var in [self.stop_job_var, self.delete_job_var]:
            if html.request.has_var(action_var):
                return True
        return False

    def handle_actions(self):
        if html.request.var(self.acknowledge_job_var):
            self.acknowledge_job()
            return True
        if html.request.var(self.stop_job_var):
            self.stop_job()
            return True
        if html.request.var(self.delete_job_var):
            self.delete_job()
            return True
        return False

    def did_acknowledge_job(self):
        return self._did_acknowledge_job

    def did_stop_job(self):
        return self._did_stop_job

    def did_delete_job(self):
        return self._did_delete_job

    def acknowledge_job(self):
        job_id = html.request.var(self.acknowledge_job_var)
        job = GUIBackgroundJob(job_id)
        if not job.is_available():
            return

        self._did_acknowledge_job = True
        job.acknowledge(config.user.id)

    def stop_job(self):
        job_id = html.request.var(self.stop_job_var)
        if not job_id:
            return

        job = GUIBackgroundJob(job_id)
        if not job.is_available():
            return

        title = _("Interuption of job")
        html.header(title, self._breadcrumb)
        if self.confirm_dialog_opened() and not job.is_active():
            html.show_message(_("No longer able to stop job. Background job just finished."))
            return

        c = html.confirm(_("Stop job %s%s?") % (job_id, self._get_extra_info(job)))
        if c and job.may_stop():
            job.stop()
            self._did_stop_job = True
            html.show_message(_("Background job has been stopped"))

    def delete_job(self):
        job_id = html.request.var(self.delete_job_var)
        if not job_id:
            return

        job = GUIBackgroundJob(job_id=job_id)
        if not job.is_available():
            return

        title = _("Deletion of job")
        html.header(title, self._breadcrumb)
        c = html.confirm(_("Delete job %s%s?") % (job_id, self._get_extra_info(job)))
        if c and job.may_delete():
            job.delete()
            self._did_delete_job = True
            html.show_message(_("Background job has been deleted"))

    def _get_extra_info(self, job):
        job_status = job.get_status()
        if job_status.get("title"):
            return " (%s)" % job_status["title"]
        return ""
