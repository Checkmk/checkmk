#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import pprint
import time
import traceback

import cmk
import cmk.store
from cmk.exceptions import MKGeneralException

import cmk.gui.i18n
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
import cmk.gui.sites as sites
import cmk.gui.config as config
import cmk.gui.log as log
import cmk.gui.table as table
import cmk.gui.background_job as background_job
from cmk.gui.background_job import JobStatus

loaded_with_language = False
def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    config.declare_permission_section("background_jobs", _("Background jobs"), do_sort = False)

    config.declare_permission("background_jobs.manage_jobs",         _("Manage background jobs"),
                   _("Allows you to see the job overview page."), ["admin"])
    config.declare_permission("background_jobs.stop_jobs",           _("Stop background jobs"),
                   _("Configures the permission to stop background jobs. Note: some jobs cannot be stopped."), ["user", "admin"])
    config.declare_permission("background_jobs.delete_jobs",         _("Delete background jobs"),
                   _("Configures the permission to delete background jobs. Note: some jobs cannot be deleted."), ["user", "admin"])
    config.declare_permission("background_jobs.see_foreign_jobs",    _("See foreign background jobs"),
                   _("Allows you to see jobs of other users."), ["admin"])
    config.declare_permission("background_jobs.stop_foreign_jobs",   _("Stop foreign background jobs"),
                   _("Allows you to stop jobs of other users. Note: some jobs cannot be stopped."), ["admin"])
    config.declare_permission("background_jobs.delete_foreign_jobs", _("Delete foreign background jobs"),
                   _("Allows you to delete jobs of other users. Note: some jobs cannot be deleted"), ["admin"])


    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()


class GUIBackgroundProcess(background_job.BackgroundProcess):
    def initialize_environment(self):
        # setup logging
        log.init_logging()
        self._logger = log.logger.getChild("background_process")
        self._log_path_hint = _("More information can be found in ~/var/log/web.log")

        # Disable html request timeout
        html.disable_request_timeout()

        # Close livestatus connections inherited from the parent process
        sites.disconnect()

        super(GUIBackgroundProcess, self).initialize_environment()



# These functions here are included in a frozen snapshot of a background job
# Restrictions for newly added functions: no function arguments, only getters
class GUIBackgroundJobSnapshottedFunctions(background_job.BackgroundJob):
    def has_exception(self):
        return self.get_status().get("state") == background_job.JobStatus.state_exception


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

        if not self.is_running():
            return False

        return True


    def may_delete(self):
        if not self.is_deletable():
            return False

        if not self.is_stoppable() and self.is_running():
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
    def is_running(self):  # pylint: disable=useless-super-delegation
        return super(GUIBackgroundJobSnapshottedFunctions, self).is_running()


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
        kwargs["user"]   = config.user.id
        kwargs["logfile_path"] = "~/var/log/web.log"
        # Deletable is currently a GUI only feature, not known in background_job
        self._deletable = kwargs.get("deletable", True)

        super(GUIBackgroundJob, self).__init__(job_id, logger=logger, **kwargs)


    def get_status_snapshot(self):
        return GUIBackgroundStatusSnapshot(self)


    def acknowledge(self, user_id):
        self.update_status({"acknowledged_by": user_id})


    @classmethod
    def get_concrete_subclasses(cls):
        # Note: Due to the strange execfile plugin mechanism, there is a risk
        #       that a class gets declared multiple times. We always use the last
        #       declaration of the given class
        classes = {}
        for subclass in cls.__subclasses__(): # pylint: disable=no-member
            classes[subclass.__name__] = subclass

        all_subclasses = []
        for subclass in classes.values():
            # Concrete subclasses have an attribute job_prefix
            if hasattr(subclass, "job_prefix"):
                all_subclasses.append(subclass)
            all_subclasses.extend(subclass.get_concrete_subclasses())

        return all_subclasses



# GUI pages are built in several phases, and each face can take a non-trivial
# amount of time. Nevertheless, it is crucial to render a consistent state of
# the background job in question. The class below provides such a status
# snapshot for the job given to the constructor.
#
# TODO: BackgroundJob should provide an explicit status object, which we can use
# here without any metaprogramming Kung Fu and arcane inheritance hierarchies.
class GUIBackgroundStatusSnapshot(object):
    def __init__(self, background_job):
        super(GUIBackgroundStatusSnapshot, self).__init__()
        self._job_status = background_job.get_status()
        self._logger = background_job._logger.getChild("snapshot")

        for name, value in GUIBackgroundJobSnapshottedFunctions.__dict__.iteritems():
            if hasattr(value, "__call__"):
                self._job_status[name] = getattr(background_job, name)()


    def get_status_as_dict(self):
        return {self.get_job_id(): self._job_status}


    def __getattr__(self, name):
        if name not in self._job_status:
            raise MKGeneralException(_("The function %s is not in the snapshotted functions.") % name)
        return lambda: self._job_status[name]




class GUIBackgroundJobManager(background_job.BackgroundJobManager):
    def __init__(self):
        super(GUIBackgroundJobManager, self).__init__(logger=log.logger.getChild("background_job_manager"))

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
            except Exception, e:
                self._logger.error(_("Exception parsing background job %s: %s") % (job_id, e))
                continue
        return visible_jobs


    def show_status_of_job_classes(self, job_classes, **kwargs):
        job_class_infos = {}
        for job_class in job_classes:
            if not hasattr(job_class, "job_prefix"):
                # Skip abstract classes
                continue
            all_job_ids = self.get_all_job_ids(job_class)
            jobs_info = self._get_job_infos(all_job_ids)
            job_class_infos[job_class] = jobs_info
        html.write(JobRenderer.render_job_class_infos(job_class_infos, **kwargs))


    def get_status_all_jobs(self, job_class):
        all_job_ids = self.get_all_job_ids(job_class)
        return self._get_job_infos(all_job_ids)


    def show_job_details(self, job_id = None, job_snapshot = None):
        job_info = self._get_job_infos([job_id])
        if not job_info:
            raise MKGeneralException("Background job with id <i>%s</i> not found" % job_id)

        job_id, job_status = job_info.items()[0]
        html.write(JobRenderer.render_job_details(job_id, job_status))


    def show_job_details_from_snapshot(self, job_snapshot):
        if job_snapshot.exists():
            job_info = job_snapshot.get_status_as_dict()
            job_id, job_status = job_info.items()[0]
            html.write(JobRenderer.render_job_details(job_id, job_status))
        else:
            raise MKGeneralException("Background job with id <i>%s</i> not found" % job_snapshot.get_job_id())



    def _get_job_infos(self, jobs):
        all_jobs = {}
        for job_id in jobs:
            try:
                job = GUIBackgroundJob(job_id)
                job_status = job.get_status()
                is_running = job.is_running()
            except Exception, e:
                self._logger.error(_("Exception parsing background job %s: %s") % (job_id, str(e)))
                continue


            if is_running and job.may_stop():
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

class JobRenderer(object):
    @classmethod
    def render_job_details(cls, job_id, job_status):
        """Renders the complete job details in a single table with left headers"""
        html.plug()
        html.open_table(class_=["data", "headerleft", "job_details"])

        # Static info
        for left, right in [
                            (_("ID"),      job_id),
                            (_("Title"),   job_status["title"]),
                            (_("Started"), cmk.render.date_and_time(job_status["started"])),
                            (_("Owner"),   job_status["user"]),
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
            html.icon_button(html.makeactionuri([(ActionHandler.stop_job_var, job_id)]),
                                                _("Stop this job"), "disable_test")
        if job_status.get("may_delete"):
            html.icon_button(html.makeactionuri([(ActionHandler.delete_job_var, job_id)]),
                                                        _("Delete this job"), "delete")
        html.close_td()
        html.close_tr()

        # Job state
        html.open_tr()
        html.th(_("State"))
        html.td(job_status["state"], css=cls.get_css_for_jobstate(job_status["state"]))
        html.close_tr()

        if job_status["state"] == background_job.JobStatus.state_exception:
            html.open_tr()
            html.th(_("Acknowledged by"))
            html.td(job_status.get("acknowledged_by", ""))
            html.close_tr()

        # Dynamic data
        progress_info = job_status.get("progress_info",
                                      background_job.BackgroundProcessInterface.parse_progress_info(""))
        runtime_info = cmk.render.timespan(job_status.get("duration", 0))
        if job_status["state"] == background_job.JobStatus.state_running and "estimated_duration" in job_status:
            runtime_info += " (%s: %s)" %  (_("estimated duration"), cmk.render.timespan(job_status["estimated_duration"]))
        for left, right in [
                            (_("Runtime"),  runtime_info),
                            (_("PID"),      job_status.get("pid", "")),
                            (_("Result"),   "<br>".join(progress_info["JobResult"])),
                           ]:
            if right == None:
                continue
            html.open_tr()
            html.th(left)
            html.td(HTML(right))
            html.close_tr()



        # Exceptions
        exceptions = progress_info["JobException"]
        if exceptions:
            html.open_tr()
            html.th(_("Exceptions"))
            html.open_td()
            if exceptions and "logfile_path" in job_status:
                exceptions.append(_("More information can be found in %s") % job_status["logfile_path"])
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
        html.pre("\n".join(progress_info["JobProgressUpdate"]))
        html.close_div()
        html.close_td()
        html.close_tr()


        html.close_table()
        html.javascript("var log = document.getElementById('progress_log'); log.scrollTop = log.scrollHeight;")
        html.unplug()
        return html.drain()


    @classmethod
    def render_job_class_infos(cls, job_class_infos, **kwargs):
        """Renders all jobs from the job_class_infos in a single multi-table"""
        html.plug()
        html.open_table(css="job_table data")
        for job_class, jobs_info in sorted(job_class_infos.items(), key=lambda x: x[0].gui_title):
            html.open_tr()
            html.open_td(colspan=len(cls.get_headers()))
            html.h3(job_class.gui_title)
            html.close_td()
            html.close_tr()

            if not jobs_info:
                html.open_tr()
                html.open_td(colspan=len(cls.get_headers()))
                html.div(_("No entries"), css="info")
                html.close_td()
                html.close_tr()
                continue

            cls.render_job_row_headers()
            odd = "even"
            for job_id, job_status in sorted(jobs_info.items(), reverse=True):
                cls.render_job_row(job_id, job_status, odd, **kwargs)
                odd = "even" if odd == "odd" else "odd"


        html.unplug()
        return html.drain()


    @classmethod
    def render_job_row_headers(cls):
        html.open_tr()
        for header in cls.get_headers():
            html.th(header)
        html.close_tr()


    @classmethod
    def get_headers(cls):
        return [_("Actions"), _("Job ID"), _("Job Title"), _("State"), _("Started"), _("Owner"),
                _("PID"), _("Runtime"), _("Last progress info"), _("Results")]


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
                                        ("back_url", job_details_back_url),
                                        ("job_id", job_id)],
                                        filename="wato.py")
        html.a(job_id, href=uri)
        html.close_td()

        # Title
        html.td(job_status.get("title", _("Background Job")), css="job_title")

        # State
        html.td(job_status["state"], css=cls.get_css_for_jobstate(job_status["state"]))

        # Started
        html.td(cmk.render.date_and_time(job_status["started"]), css="job_started")

        # Owner
        html.td(job_status.get("user", _("Unknown user")), css="job_owner")

        # PID
        html.td(job_status.get("pid", ""), css="job_pid")

        # Druation
        html.td(cmk.render.timespan(job_status.get("duration", 0)), css="job_runtime")

        # Progress info
        progress_info = job_status.get("progress_info")
        if progress_info:
            if job_status.get("state") ==  background_job.JobStatus.state_exception:
                html.td(HTML("<br>".join(progress_info["JobException"])), css="job_last_progress")
            else:
                progress_text = ""
                if progress_info["JobProgressUpdate"]:
                    progress_text += "%s" % progress_info["JobProgressUpdate"][-1]
                html.td(HTML(progress_text), css="job_last_progress")

            html.td(HTML("<br>".join(progress_info["JobResult"])), css="job_result")
        else:
            html.td("", css="job_last_progress")
            html.td("", css="job_result")


    @classmethod
    def get_css_for_jobstate(cls, job_state):
        job_css_map = {background_job.JobStatus.state_initialized  : "job_state job_initialized",
                       background_job.JobStatus.state_running      : "job_state job_running",
                       background_job.JobStatus.state_exception    : "job_state job_exception",
                       background_job.JobStatus.state_stopped      : "job_state job_exception", # same css as exception
                       background_job.JobStatus.state_finished     : "job_state job_finished" }
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


class ActionHandler(object):
    stop_job_var        = "_stop_job"
    delete_job_var      = "_delete_job"
    acknowledge_job_var = "_acknowledge_job"

    def __init__(self, stylesheets=None):
        super(ActionHandler, self).__init__()
        self._stylesheets = stylesheets
        self._did_acknowledge_job = False
        self._did_stop_job   = False
        self._did_delete_job = False


    def confirm_dialog_opened(self):
        for action_var in [self.stop_job_var, self.delete_job_var]:
            if html.has_var(action_var):
                return True
        return False


    def handle_actions(self):
        if html.var(self.acknowledge_job_var):
            self.acknowledge_job()
            return True
        if html.var(self.stop_job_var):
            self.stop_job()
            return True
        elif html.var(self.delete_job_var):
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
        job_id = html.var(self.acknowledge_job_var)
        job = GUIBackgroundJob(job_id)
        if not job.is_available():
            return

        self._did_acknowledge_job = True
        job.acknowledge(config.user.id)


    def stop_job(self):
        job_id = html.var(self.stop_job_var)
        if not job_id:
            return

        job = GUIBackgroundJob(job_id)
        if not job.is_available():
            return

        html.header("Interuption of job", stylesheets=self._stylesheets)
        if self.confirm_dialog_opened() and not job.is_running():
            html.message(_("No longer able to stop job. Background job just finished."))
            return

        c = html.confirm(_("Stop job %s%s?") % (job_id, self._get_extra_info(job)))
        if c and job.may_stop():
            job.stop()
            self._did_stop_job = True
            html.message(_("Background job has been stopped"))


    def delete_job(self):
        job_id = html.var(self.delete_job_var)
        if not job_id:
            return

        job = GUIBackgroundJob(job_id=job_id)
        if not job.is_available():
            return

        html.header("Deletion of job", stylesheets=self._stylesheets)
        c = html.confirm(_("Delete job %s%s?") % (job_id, self._get_extra_info(job)))
        if c and job.may_delete():
            job.delete()
            self._did_delete_job = True
            html.message(_("Background job has been deleted"))


    def _get_extra_info(self, job):
        job_status = job.get_status()
        if job_status.get("title"):
            return " (%s)" % job_status["title"]
        return ""
