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

# This module implements generic functionality of the Check_MK backup
# system. It is used to configure the site and system backup.
#
# BE AWARE: This code is directly used by the appliance. So if you are
# about to refactor things, you will have to care about the appliance!

import abc
import errno
import glob
import os
import shutil
import signal
import socket
import subprocess
import time
import json
import six

import cmk.utils.render as render
import cmk.utils.store as store
from cmk.utils.schedule import next_scheduled_time

import cmk.gui.forms as forms
from cmk.gui.table import table_element
import cmk.gui.key_mgmt as key_mgmt
from cmk.gui.valuespec import (
    Password,
    Dictionary,
    TextUnicode,
    DropdownChoice,
    Checkbox,
    Alternative,
    FixedValue,
    CascadingDropdown,
    ID,
    AbsoluteDirname,
    SchedulePeriod,
    ListOf,
    Timeofday,
)
from cmk.gui.exceptions import HTTPRedirect, MKUserError, MKGeneralException
from cmk.gui.i18n import _
from cmk.gui.globals import html

#.
#   .--Config--------------------------------------------------------------.
#   |                     ____             __ _                            |
#   |                    / ___|___  _ __  / _(_) __ _                      |
#   |                   | |   / _ \| '_ \| |_| |/ _` |                     |
#   |                   | |__| (_) | | | |  _| | (_| |                     |
#   |                    \____\___/|_| |_|_| |_|\__, |                     |
#   |                                           |___/                      |
#   +----------------------------------------------------------------------+
#   | Handling of the backup configuration files. This is used to handle   |
#   | either the global system config for the appliance and the site       |
#   | specific configuration of the site backup.                           |
#   '----------------------------------------------------------------------'


def is_site():
    return "OMD_ROOT" in os.environ


def mkbackup_path():
    if not is_site():
        return "/usr/sbin/mkbackup"
    return "%s/bin/mkbackup" % os.environ["OMD_ROOT"]


def system_config_path():
    return "/etc/cma/backup.conf"


def site_config_path(site_id=None):
    if site_id is None:
        if not is_site():
            raise Exception(_("Not executed in OMD environment!"))
        site_id = os.environ["OMD_SITE"]

    return "/omd/sites/%s/etc/check_mk/backup.mk" % site_id


def hostname():
    return socket.gethostname()


def is_cma():
    return os.path.exists("/etc/cma/cma.conf")


def is_canonical(directory):
    if not directory.endswith("/"):
        directory += "/"
    return (os.path.isabs(directory) and
            os.path.commonprefix([os.path.realpath(directory) + '/', directory]) == directory)


# TODO: Locking!
class Config(object):
    def __init__(self, file_path):
        self._file_path = file_path

    def load(self):
        return store.load_object_from_file(self._file_path, default={
            "targets": {},
            "jobs": {},
        })

    def save(self, config):
        store.save_object_to_file(self._file_path, config)


#.
#   .--Abstract------------------------------------------------------------.
#   |                 _    _         _                  _                  |
#   |                / \  | |__  ___| |_ _ __ __ _  ___| |_                |
#   |               / _ \ | '_ \/ __| __| '__/ _` |/ __| __|               |
#   |              / ___ \| |_) \__ \ |_| | | (_| | (__| |_                |
#   |             /_/   \_\_.__/|___/\__|_|  \__,_|\___|\__|               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class BackupEntity(object):
    def __init__(self, ident, config):
        self._ident = ident
        self._config = {}

        self.from_config(config)

    def ident(self):
        return self._ident

    def config(self):
        return self._config

    def title(self):
        return self._config["title"]

    def to_config(self):
        return self._config

    def from_config(self, config):
        self._config = config


class BackupEntityCollection(object):
    def __init__(self, config_file_path, cls, config_attr):
        self._config_path = config_file_path
        self._config = Config(config_file_path).load()
        self._cls = cls
        self._config_attr = config_attr
        self.objects = dict([
            (ident, cls(ident, config)) for ident, config in self._config[config_attr].items()
        ])

    def get(self, ident):
        return self.objects[ident]

    def remove(self, obj):
        try:
            del self.objects[obj.ident()]
        except KeyError:
            pass

    def choices(self):
        return sorted([(ident, obj.title()) for ident, obj in self.objects.items()],
                      key=lambda x_y: x_y[1].title())

    def add(self, obj):
        self.objects[obj.ident()] = obj

    def save(self):
        self._config[self._config_attr] = dict([
            (ident, obj.to_config()) for ident, obj in self.objects.items()
        ])
        Config(self._config_path).save(self._config)


#.
#   .--Jobs----------------------------------------------------------------.
#   |                            _       _                                 |
#   |                           | | ___ | |__  ___                         |
#   |                        _  | |/ _ \| '_ \/ __|                        |
#   |                       | |_| | (_) | |_) \__ \                        |
#   |                        \___/ \___/|_.__/|___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Backup job handling. A backup job is the entity to describe a single |
#   | backup process which has it's own state, can be executed manually    |
#   | and also scheduled to be executed in a predefined interval.          |
#   '----------------------------------------------------------------------'


# Abstract class for backup jobs (Job) and restore job (RestoreJob)
class MKBackupJob(object):
    @classmethod
    def state_name(cls, state):
        return {
            "started": _("Started"),
            "running": _("Currently running"),
            "finished": _("Ended"),
            None: _("Never executed"),
        }[state]

    def state_file_path(self):
        raise NotImplementedError()

    def cleanup(self):
        try:
            os.unlink(self.state_file_path())
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise

    def state(self):
        try:
            state = json.load(open(self.state_file_path()))
        except IOError as e:
            if e.errno == errno.ENOENT:  # not existant
                state = {
                    "state": None,
                    "started": None,
                    "output": "",
                }
            else:
                raise
        except Exception as e:
            raise MKGeneralException(
                _("Failed to parse state file \"%s\": %s") % (self.state_file_path(), e))

        # Fix data structure when the process has been killed
        if state["state"] == "running" and not os.path.exists("/proc/%d" % state["pid"]):
            state.update({
                "state": "finished",
                "finished": max(state["started"],
                                os.stat(self.state_file_path()).st_mtime),
                "success": False,
            })

        return state

    def was_started(self):
        return os.path.exists(self.state_file_path())

    def is_running(self):
        if not self.was_started():
            return False

        state = self.state()
        return state["state"] in [ "started", "running" ] \
               and os.path.exists("/proc/%d" % state["pid"])

    def start(self, env=None):
        p = subprocess.Popen(self._start_command(),
                             close_fds=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             stdin=open(os.devnull),
                             env=env)
        output = p.stdout.read()
        if p.wait() != 0:
            raise MKGeneralException(_("Failed to start the job: %s") % output)

    def _start_command(self):
        raise NotImplementedError()

    def stop(self):
        state = self.state()
        pgid = os.getpgid(state["pid"])

        try:
            os.killpg(pgid, signal.SIGTERM)
        except OSError as e:
            if e.errno == errno.ESRCH:
                pass
            else:
                raise

        wait = 5  # sec
        while os.path.exists("/proc/%d" % state["pid"]) and wait > 0:
            time.sleep(0.5)
            wait -= 0.5

        # When still running after 5 seconds, enforce
        if wait == 0:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    pass
                else:
                    raise


class Job(MKBackupJob, BackupEntity):
    def target_ident(self):
        return self._config["target"]

    def key_ident(self):
        return self._config["encrypt"]

    def is_encrypted(self):
        return self._config["encrypt"] is not None

    # TODO: Duplicated code with mkbackup (globalize_job_id())
    def global_ident(self):
        parts = []
        site = os.environ.get("OMD_SITE")

        if site:
            parts.append("Check_MK")
        else:
            parts.append("Check_MK_Appliance")

        parts.append(hostname())

        if site:
            parts.append(site)

        parts.append(self._ident)

        return "-".join([p.replace("-", "+") for p in parts])

    def state_file_path(self):
        if not is_site():
            path = "/var/lib/mkbackup"
        else:
            path = "%s/var/check_mk/backup" % os.environ["OMD_ROOT"]

        return "%s/%s.state" % (path, self.ident())

    def _start_command(self):
        return [mkbackup_path(), "backup", "--background", self.ident()]

    def schedule(self):
        return self._config["schedule"]

    def cron_config(self):
        if not self._config["schedule"] or self._config["schedule"]["disabled"]:
            return
        userspec = self._cron_userspec()
        cmdline = self._cron_cmdline()
        return ["%s %s%s" % (timespec, userspec, cmdline) for timespec in self._cron_timespecs()]

    def _cron_timespecs(self):
        period = self._config["schedule"]["period"]
        times = self._config["schedule"]["timeofday"]

        if period == "day":
            dayspec = "* * *"

        elif period[0] == "week":
            # 0-6
            dayspec = "* * %d" % (period[1] + 1,)

        elif period[0] == "month_begin":
            # 1-28
            dayspec = "%d * *" % period[1]

        else:
            raise NotImplementedError()

        # times: list of two element tuples (hours, minutes)
        timespecs = []
        for hour, minute in times:
            timespecs.append("%d %d %s" % (minute, hour, dayspec))

        return timespecs

    def _cron_userspec(self):
        if os.environ.get("OMD_SITE"):
            return ""
        return "root "

    def _cron_cmdline(self):
        return "mkbackup backup %s >/dev/null" % self.ident()


class Jobs(BackupEntityCollection):
    def __init__(self, config_file_path):
        super(Jobs, self).__init__(config_file_path, cls=Job, config_attr="jobs")

        etc_path = os.path.dirname(os.path.dirname(config_file_path))
        self._cronjob_path = "%s/cron.d/mkbackup" % etc_path

    def show_list(self, editable=True):
        html.h2(_("Jobs"))
        with table_element(sortable=False, searchable=False) as table:

            for job_ident, job in sorted(self.objects.items()):
                table.row()
                table.cell(_("Actions"), css="buttons")
                delete_url = html.makeactionuri_contextless([("mode", "backup"),
                                                             ("_action", "delete"),
                                                             ("_job", job_ident)])
                edit_url = html.makeuri_contextless([("mode", "edit_backup_job"),
                                                     ("job", job_ident)])
                state_url = html.makeuri_contextless([("mode", "backup_job_state"),
                                                      ("job", job_ident)])

                state = job.state()

                if editable and not job.is_running():
                    html.icon_button(edit_url, _("Edit this backup job"), "edit")
                    html.icon_button(delete_url, _("Delete this backup job"), "delete")

                if state["state"] is not None:
                    html.icon_button(state_url, _("Show current / last state of this backup job"),
                                     "backup_state")

                if not job.is_running():
                    start_url = html.makeactionuri_contextless([
                        ("mode", "backup"),
                        ("_action", "start"),
                        ("_job", job_ident),
                    ])

                    html.icon_button(start_url, _("Manually start this backup"), "backup_start")
                else:
                    stop_url = html.makeactionuri_contextless([
                        ("mode", "backup"),
                        ("_action", "stop"),
                        ("_job", job_ident),
                    ])

                    html.icon_button(stop_url, _("Stop this backup job"), "backup_stop")

                table.cell(_("Name"), html.render_text(job.title()))

                css = "state0"
                state_txt = job.state_name(state["state"])
                if state["state"] == "finished":
                    if not state["success"]:
                        css = "state2"
                        state_txt = _("Failed")
                    else:
                        state_txt = _("Finished")
                elif state["state"] is None:
                    css = ""

                table.cell(_("State"), css=css)
                html.write(html.render_text(state_txt))

                table.cell(_("Runtime"))
                if state["started"]:
                    html.write(_("Started at %s") % render.date_and_time(state["started"]))
                    duration = time.time() - state["started"]
                    if state["state"] == "finished":
                        html.write(", Finished at %s" % render.date_and_time(state["finished"]))
                        duration = state["finished"] - state["started"]

                    if "size" in state:
                        size_txt = "Size: %s, " % render.fmt_bytes(state["size"])
                    else:
                        size_txt = ""

                    html.write(
                        _(" (Duration: %s, %sIO: %s/s)") % (
                            render.timespan(duration),
                            size_txt,
                            render.fmt_bytes(state["bytes_per_second"]),
                        ))

                table.cell(_("Next run"))
                schedule = job.schedule()
                if not schedule:
                    html.write(_("Only execute manually"))

                elif schedule["disabled"]:
                    html.write(_("Disabled"))

                else:
                    # find the next time of all configured times
                    times = []
                    for timespec in schedule["timeofday"]:
                        times.append(next_scheduled_time(schedule["period"], timespec))

                    html.write(time.strftime("%Y-%m-%d %H:%M", time.localtime(min(times))))

    def jobs_using_target(self, target):
        jobs = []
        for job in self.objects.values():
            if job.target_ident() == target.ident():
                jobs.append(job)
        return jobs

    def save(self):
        super(Jobs, self).save()
        self.save_cronjobs()

    def save_cronjobs(self):
        with open(self._cronjob_path, "w") as f:
            self._write_cronjob_header(f)
            for job in self.objects.values():
                cron_config = job.cron_config()
                if cron_config:
                    f.write("%s\n" % "\n".join(cron_config))

        self._apply_cron_config()

    def _write_cronjob_header(self, f):
        f.write("# Written by mkbackup configuration\n")

    def _apply_cron_config(self):
        pass


class PageBackup(object):
    def title(self):
        raise NotImplementedError()

    def jobs(self):
        raise NotImplementedError()

    def keys(self):
        raise NotImplementedError()

    def home_button(self):
        raise NotImplementedError()

    def buttons(self):
        self.home_button()
        html.context_button(_("Backup targets"),
                            html.makeuri_contextless([("mode", "backup_targets")]),
                            "backup_targets")
        html.context_button(_("Backup keys"), html.makeuri_contextless([("mode", "backup_keys")]),
                            "backup_key")
        if self._may_edit_config():
            html.context_button(_("New job"),
                                html.makeuri_contextless([("mode", "edit_backup_job")]),
                                "backup_job_new")
        html.context_button(_("Restore"), html.makeuri_contextless([("mode", "backup_restore")]),
                            "backup_restore")

    def _may_edit_config(self):
        return True

    def action(self):
        ident = html.request.var("_job")
        jobs = self.jobs()
        try:
            job = jobs.get(ident)
        except KeyError:
            raise MKUserError("_job", _("This backup job does not exist."))

        action = html.request.var("_action")

        if action == "delete":
            if not html.transaction_valid():
                return
        else:
            if not html.check_transaction():
                return

        if action == "delete" and self._may_edit_config():
            return self._delete_job(job)

        elif action == "start":
            return self._start_job(job)

        elif action == "stop":
            return self._stop_job(job)

        else:
            raise NotImplementedError()

    def _delete_job(self, job):
        if job.is_running():
            raise MKUserError("_job", _("This job is currently running."))

        if html.confirm(_("Do you really want to delete this job?"), add_header=self.title()):
            html.check_transaction()  # invalidate transid
            job.cleanup()
            jobs = self.jobs()
            jobs.remove(job)
            jobs.save()
            return None, _("The job has been deleted.")

    def _start_job(self, job):
        job.start()
        return None, _("The backup has been started.")

    def _stop_job(self, job):
        job.stop()
        return None, _("The backup has been stopped.")

    def page(self):
        show_key_download_warning(self.keys().load())
        self.jobs().show_list(editable=self._may_edit_config())


class PageEditBackupJob(object):
    def __init__(self):
        super(PageEditBackupJob, self).__init__()
        job_ident = html.request.var("job")

        if job_ident is not None:
            try:
                job = self.jobs().get(job_ident)
            except KeyError:
                raise MKUserError("target", _("This backup job does not exist."))

            if job.is_running():
                raise MKUserError("_job", _("This job is currently running."))

            self._new = False
            self._ident = job_ident
            self._job_cfg = job.to_config()
            self._title = _("Edit backup job: %s") % job.title()
        else:
            self._new = True
            self._ident = None
            self._job_cfg = {}
            self._title = _("New backup job")

    def jobs(self):
        raise NotImplementedError()

    def targets(self):
        raise NotImplementedError()

    def keys(self):
        raise NotImplementedError()

    def title(self):
        return self._title

    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup")]), "back")

    def vs_backup_schedule(self):
        return Alternative(
            title=_("Schedule"),
            style="dropdown",
            elements=[
                FixedValue(
                    None,
                    title=_("Execute manually"),
                    totext=_("Only execute manually"),
                ),
                Dictionary(
                    title=_("Schedule execution"),
                    elements=[
                        ("disabled",
                         Checkbox(
                             title=_("Disable"),
                             label=_("Currently disable scheduled execution of this job"),
                         )),
                        ("period", SchedulePeriod(from_end=False)),
                        ("timeofday",
                         ListOf(
                             Timeofday(default_value=(0, 0),),
                             title=_("Time of day to start the backup at"),
                             movable=False,
                             default_value=[(0, 0)],
                             add_label=_("Add new time"),
                             empty_text=_("Please specify at least one time."),
                             allow_empty=False,
                         )),
                    ],
                    optional_keys=[],
                ),
            ])

    def vs_backup_job(self):
        if self._new:
            ident_attr = [(
                "ident",
                ID(title=_("Unique ID"),
                   help=_(
                       "The ID of the job must be a unique text. It will be used as an internal key "
                       "when objects refer to the job."),
                   allow_empty=False,
                   size=12,
                   validate=self._validate_backup_job_ident))]
        else:
            ident_attr = [(
                "ident",
                FixedValue(self._ident, title=_("Unique ID")),
            )]

        return Dictionary(
            title=_("Backup job"),
            elements=ident_attr + [
                ("title", TextUnicode(
                    title=_("Title"),
                    allow_empty=False,
                    size=64,
                )),
                ("target",
                 DropdownChoice(
                     title=_("Target"),
                     choices=self.backup_target_choices,
                     validate=self._validate_target,
                     invalid_choice="complain",
                 )),
                ("schedule", self.vs_backup_schedule()),
                ("compress",
                 Checkbox(title=_("Compression"),
                          help=_("Enable gzip compression of the backed up files. The tar archives "
                                 "created by the backup are gzipped during backup."),
                          label=_("Compress the backed up files"))),
                ("encrypt",
                 Alternative(title=_("Encryption"),
                             help=_("Enable encryption of the backed up files. The tar archives "
                                    "created by the backup are encrypted using the specified key "
                                    "during backup. You will need the private key and the "
                                    "passphrase to decrypt the backup."),
                             style="dropdown",
                             elements=[
                                 FixedValue(
                                     None,
                                     title=_("Do not encrypt the backup"),
                                     totext="",
                                 ),
                                 DropdownChoice(
                                     title=_("Encrypt the backup using the key:"),
                                     choices=self.backup_key_choices,
                                     invalid_choice="complain",
                                 ),
                             ])),
            ] + self.custom_job_attributes(),
            optional_keys=[],
            render="form",
        )

    def _validate_target(self, value, varprefix):
        self.targets().validate_target(value, varprefix)

    # Can be overridden by subclasses to add custom attributes to the
    # job configuration. e.g. system jobs can exclude sites optionally.
    def custom_job_attributes(self):
        return []

    def _validate_backup_job_ident(self, value, varprefix):
        if value == "restore":
            raise MKUserError(varprefix, _("You need to choose another ID."))

        if value in self.jobs().objects:
            raise MKUserError(varprefix, _("This ID is already used by another backup job."))

    def backup_key_choices(self):
        return self.keys().choices()

    def backup_target_choices(self):
        return sorted(self.targets().choices(), key=lambda x_y1: x_y1[1].title())

    def action(self):
        if html.transaction_valid():
            vs = self.vs_backup_job()

            config = vs.from_html_vars("edit_job")
            vs.validate_value(config, "edit_job")

            if "ident" in config:
                self._ident = config.pop("ident")
            self._job_cfg = config

            jobs = self.jobs()
            if self._new:
                job = Job(self._ident, self._job_cfg)
                jobs.add(job)
            else:
                job = jobs.get(self._ident)
                job.from_config(self._job_cfg)

            jobs.save()
        raise HTTPRedirect(html.makeuri_contextless([("mode", "backup")]))

    def page(self):
        html.begin_form("edit_job", method="POST")
        html.prevent_password_auto_completion()

        vs = self.vs_backup_job()

        vs.render_input("edit_job", self._job_cfg)
        vs.set_focus("edit_job")
        forms.end()

        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()


class PageAbstractBackupJobState(object):
    def __init__(self):
        super(PageAbstractBackupJobState, self).__init__()
        self._job = None
        self._ident = None

    def jobs(self):
        raise NotImplementedError()

    def title(self):
        return _("Job state: %s") % self._job.title()

    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup")]), "back")

    def page(self):
        html.open_div(id_="job_details")
        self.show_job_details()
        html.close_div()
        html.javascript("cmk.backup.refresh_job_details('%s', '%s', %s)" %
                        (self._update_url(), self._ident, "true" if is_site() else "false"))

    def _update_url(self):
        return "ajax_backup_job_state.py?job=%s" % self._ident

    def show_job_details(self):
        job = self._job
        state = job.state()

        html.open_table(class_=["data", "backup_job"])

        css = "state0"
        state_txt = job.state_name(state["state"])
        if state["state"] == "finished":
            if not state["success"]:
                css = "state2"
                state_txt = _("Failed")
            else:
                state_txt = _("Finished")
        elif state["state"] is None:
            css = None

        html.open_tr(class_=["data", "even0"])
        html.td(_("State"), class_=["left", "legend"])
        html.open_td(class_=["state", css])
        html.write(state_txt)
        html.close_td()
        html.close_tr()

        html.open_tr(class_=["data", "odd0"])
        html.td(_("Runtime"), class_="left")
        html.open_td()
        if state["started"]:
            html.write(_("Started at %s") % render.date_and_time(state["started"]))
            duration = time.time() - state["started"]
            if state["state"] == "finished":
                html.write(", Finished at %s" % render.date_and_time(state["started"]))
                duration = state["finished"] - state["started"]

            html.write(_(" (Duration: %s)") % render.timespan(duration))
        html.close_td()
        html.close_tr()

        html.open_tr(class_=["data", "even0"])
        html.td(_("Output"), class_=["left", "legend"])
        html.open_td()
        html.open_div(class_="log_output", style="height: 400px;", id_="progress_log")
        html.pre(state["output"])
        html.close_div()
        html.close_td()
        html.close_tr()

        html.close_table()


class PageBackupJobState(PageAbstractBackupJobState):
    def __init__(self):
        super(PageBackupJobState, self).__init__()
        self._from_vars()

    def _from_vars(self):
        job_ident = html.request.var("job")
        if job_ident is not None:
            try:
                self._job = self.jobs().get(job_ident)
            except KeyError:
                raise MKUserError("job", _("This backup job does not exist."))

            self._ident = job_ident
        else:
            raise MKUserError("job", _("You need to specify a backup job."))


#.
#   .--Targets-------------------------------------------------------------.
#   |                  _____                    _                          |
#   |                 |_   _|_ _ _ __ __ _  ___| |_ ___                    |
#   |                   | |/ _` | '__/ _` |/ _ \ __/ __|                   |
#   |                   | | (_| | | | (_| |  __/ |_\__ \                   |
#   |                   |_|\__,_|_|  \__, |\___|\__|___/                   |
#   |                                |___/                                 |
#   +----------------------------------------------------------------------+
#   | Specifying backup targets, the user tells the backup system which    |
#   | destinations can be used for the backups. Each destination has it's  |
#   | own protocol and specific parameters to specify how to backup.       |
#   '----------------------------------------------------------------------'


class Target(BackupEntity):
    def type_ident(self):
        return self._config["remote"][0]

    def type_class(self):
        return ABCBackupTargetType.get_type(self.type_ident())

    def type_params(self):
        return self._config["remote"][1]

    def type(self):
        if self.type_ident() != "local":
            raise NotImplementedError()
        return self.type_class()(self.type_params())

    def show_backup_list(self, only_type):
        with table_element(sortable=False, searchable=False) as table:

            for backup_ident, info in sorted(self.backups().items()):
                if info["type"] != only_type:
                    continue

                table.row()
                table.cell(_("Actions"), css="buttons")

                delete_url = html.makeactionuri([("_action", "delete"), ("_backup", backup_ident)])
                html.icon_button(delete_url, _("Delete this backup"), "delete")

                start_url = html.makeactionuri([("_action", "start"), ("_backup", backup_ident)])

                html.icon_button(start_url, _("Start restore of this backup"),
                                 "backup_restore_start")

                from_info = info["hostname"]
                if "site_id" in info:
                    from_info += " (Site: %s, Version: %s)" % (info["site_id"],
                                                               info["site_version"])
                else:
                    from_info += " (Version: %s)" % info["cma_version"]

                table.cell(_("Backup-ID"), html.render_text(backup_ident))
                table.cell(_("From"), html.render_text(from_info))
                table.cell(_("Finished"), render.date_and_time(info["finished"]))
                table.cell(_("Size"), render.fmt_bytes(info["size"]))
                table.cell(_("Encrypted"))
                if info["config"]["encrypt"] is not None:
                    html.write(info["config"]["encrypt"])
                else:
                    html.write_text(_("No"))

                if info["type"] == "Appliance":
                    table.cell(_("Clustered"))
                    if "cma_cluster" not in info:
                        html.write(_("Standalone"))
                    else:
                        html.write(_("Clustered"))
                        if not info["cma_cluster"]["is_inactive"]:
                            html.write(" (%s)" % _("Active node"))
                        else:
                            html.write(" (%s)" % _("Standby node"))

    def backups(self):
        return self.type().backups()

    def get_backup(self, backup_ident):
        return self.type().get_backup(backup_ident)

    def remove_backup(self, backup_ident):
        self.type().remove_backup(backup_ident)


class Targets(BackupEntityCollection):
    def __init__(self, config_file_path):
        super(Targets, self).__init__(config_file_path, cls=Target, config_attr="targets")

    def show_list(self, title=None, editable=True):
        title = title if title else _("Targets")
        html.open_h2()
        html.write(title)
        html.close_h2()
        if not editable and is_site():
            html.write("<p>%s</p>" % _("These backup targets can not be edited here. You need to "
                                       "open the device backup management."))

        with table_element(sortable=False, searchable=False) as table:

            for target_ident, target in sorted(self.objects.items()):
                table.row()
                table.cell(_("Actions"), css="buttons")
                restore_url = html.makeuri_contextless([("mode", "backup_restore"),
                                                        ("target", target_ident)])
                html.icon_button(restore_url, _("Restore from this backup target"),
                                 "backup_restore")

                if editable:
                    delete_url = html.makeactionuri_contextless([("mode", "backup_targets"),
                                                                 ("target", target_ident)])
                    edit_url = html.makeuri_contextless([("mode", "edit_backup_target"),
                                                         ("target", target_ident)])

                    html.icon_button(edit_url, _("Edit this backup target"), "edit")
                    html.icon_button(delete_url, _("Delete this backup target"), "delete")

                table.cell(_("Title"), html.render_text(target.title()))

                target_class = target.type_class()
                vs_target = target_class(target.type_params()).valuespec()
                table.cell(_("Destination"), vs_target.value_to_text(target.type_params()))

    def validate_target(self, value, varprefix):
        target = self.get(value)
        path = target.type_params()["path"]
        target.type().validate_local_directory(path, varprefix)


class PageBackupTargets(object):
    def title(self):
        raise NotImplementedError()

    def targets(self):
        raise NotImplementedError()

    def jobs(self):
        raise NotImplementedError()

    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup")]), "back")
        if self._may_edit_config():
            html.context_button(_("New backup target"),
                                html.makeuri_contextless([("mode", "edit_backup_target")]),
                                "backup_target_edit")

    def action(self):
        if html.transaction_valid():
            ident = html.request.var("target")
            targets = self.targets()
            try:
                target = targets.get(ident)
            except KeyError:
                raise MKUserError("target", _("This backup target does not exist."))

            self._verify_not_used(target)

            confirm = html.confirm(_("Do you really want to delete this target?"),
                                   add_header=self.title())

            if confirm is False:
                return False

            elif confirm:
                targets.remove(target)
                targets.save()
                return None, _("The target has been deleted.")

    def _verify_not_used(self, target):
        job_titles = [j.title() for j in self.jobs().jobs_using_target(target)]
        if job_titles:
            raise MKUserError(
                "target",
                _("You can not delete this target because it is used "
                  "by these backup jobs: %s") % ", ".join(job_titles))

    def page(self):
        self.targets().show_list()
        SystemBackupTargetsReadOnly().show_list(editable=False, title=_("System global targets"))

    def _may_edit_config(self):
        return True


class PageEditBackupTarget(object):
    def __init__(self):
        super(PageEditBackupTarget, self).__init__()
        target_ident = html.request.var("target")

        if target_ident is not None:
            try:
                target = self.targets().get(target_ident)
            except KeyError:
                raise MKUserError("target", _("This backup target does not exist."))

            self._new = False
            self._ident = target_ident
            self._target_cfg = target.to_config()
            self._title = _("Edit backup target: %s") % target.title()
        else:
            self._new = True
            self._ident = None
            self._target_cfg = {}
            self._title = _("New backup target")

    def targets(self):
        raise NotImplementedError()

    def title(self):
        return self._title

    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup_targets")]),
                            "back")

    def vs_backup_target(self):
        if self._new:
            ident_attr = [
                ("ident",
                 ID(
                     title=_("Unique ID"),
                     help=_(
                         "The ID of the target must be a unique text. It will be used as an internal key "
                         "when objects refer to the target."),
                     allow_empty=False,
                     size=12,
                     validate=self.validate_backup_target_ident,
                 )),
            ]
        else:
            ident_attr = [
                ("ident", FixedValue(
                    self._ident,
                    title=_("Unique ID"),
                )),
            ]

        return Dictionary(
            title=_("Backup target"),
            elements=ident_attr + [
                ("title", TextUnicode(
                    title=_("Title"),
                    allow_empty=False,
                    size=64,
                )),
                ("remote",
                 CascadingDropdown(
                     title=_("Destination"),
                     choices=ABCBackupTargetType.choices,
                 )),
            ],
            optional_keys=[],
            render="form",
        )

    def validate_backup_target_ident(self, value, varprefix):
        if value in self.targets().objects:
            raise MKUserError(varprefix, _("This ID is already used by another backup target."))

    def action(self):
        if html.transaction_valid():
            vs = self.vs_backup_target()

            config = vs.from_html_vars("edit_target")
            vs.validate_value(config, "edit_target")

            if "ident" in config:
                self._ident = config.pop("ident")
            self._target_cfg = config

            targets = self.targets()
            if self._new:
                target = Target(self._ident, self._target_cfg)
                targets.add(target)
            else:
                target = targets.get(self._ident)
                target.from_config(self._target_cfg)

            targets.save()
        raise HTTPRedirect(html.makeuri_contextless([("mode", "backup_targets")]))

    def page(self):
        html.begin_form("edit_target", method="POST")
        html.prevent_password_auto_completion()

        vs = self.vs_backup_target()

        vs.render_input("edit_target", self._target_cfg)
        vs.set_focus("edit_target")
        forms.end()

        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()


class SystemBackupTargetsReadOnly(Targets):
    def __init__(self):
        super(SystemBackupTargetsReadOnly, self).__init__(system_config_path())

    # Only show the list on CMA devices
    def show_list(self, title=None, editable=True):
        if is_cma():
            super(SystemBackupTargetsReadOnly, self).show_list(title, editable)


#.
#   .--Target Types--------------------------------------------------------.
#   |      _____                    _     _____                            |
#   |     |_   _|_ _ _ __ __ _  ___| |_  |_   _|   _ _ __   ___  ___       |
#   |       | |/ _` | '__/ _` |/ _ \ __|   | || | | | '_ \ / _ \/ __|      |
#   |       | | (_| | | | (_| |  __/ |_    | || |_| | |_) |  __/\__ \      |
#   |       |_|\__,_|_|  \__, |\___|\__|   |_| \__, | .__/ \___||___/      |
#   |                    |___/                 |___/|_|                    |
#   +----------------------------------------------------------------------+
#   | A target type implements the handling of different protocols to use  |
#   | for storing the backup to, like NFS, a local directory or SSH/SFTP.  |
#   '----------------------------------------------------------------------'


class ABCBackupTargetType(six.with_metaclass(abc.ABCMeta, object)):
    @abc.abstractproperty
    def ident(self):
        raise NotImplementedError()

    @classmethod
    def choices(cls):
        choices = []
        # TODO: subclasses with the same name may be registered multiple times, due to execfile
        for type_class in cls.__subclasses__():  # pylint: disable=no-member
            choices.append((type_class.ident, type_class.title(), type_class.valuespec()))
        return sorted(choices, key=lambda x: x[1])

    @classmethod
    def get_type(cls, type_ident):
        # TODO: subclasses with the same name may be registered multiple times, due to execfile
        for type_class in cls.__subclasses__():  # pylint: disable=no-member
            if type_class.ident == type_ident:
                return type_class

    @classmethod
    def title(cls):
        raise NotImplementedError()

    def __init__(self, params):
        self._params = params

    @abc.abstractmethod
    def valuespec(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def backups(self):
        raise NotImplementedError()


class BackupTargetLocal(ABCBackupTargetType):
    ident = "local"

    @classmethod
    def title(cls):
        return _("Local path")

    @classmethod
    def valuespec(cls):
        return Dictionary(
            elements=[
                ("path",
                 AbsoluteDirname(
                     title=_("Directory to save the backup to"),
                     help=_("This can be a local directory of your choice. You can also use this "
                            "option if you want to save your backup to a network share using "
                            "NFS, Samba or similar. But you will have to care about mounting the "
                            "network share on your own."),
                     allow_empty=False,
                     validate=cls.validate_local_directory,
                     size=64,
                 )),
                ("is_mountpoint",
                 Checkbox(
                     title=_("Mountpoint"),
                     label=_("Is mountpoint"),
                     help=_("When this is checked, the backup ensures that the configured path "
                            "is a mountpoint. If there is no active mount on the path, the backup "
                            "fails with an error message."),
                     default_value=True,
                 )),
            ],
            optional_keys=[],
        )

    @classmethod
    def validate_local_directory(cls, value, varprefix):
        if not is_canonical(value):
            raise MKUserError(varprefix, _("You have to provide a canonical path."))

        if is_cma() and not value.startswith("/mnt/"):
            raise MKUserError(
                varprefix,
                _("You can only use mountpoints below the <tt>/mnt</tt> "
                  "directory as backup targets."))

        if not os.path.isdir(value):
            raise MKUserError(
                varprefix,
                _("The path does not exist or is not a directory. You "
                  "need to specify an already existing directory."))

        # Check write access for the site user
        try:
            test_file_path = os.path.join(value, "write_test_%d" % time.time())
            open(test_file_path, "w")
            os.unlink(test_file_path)
        except IOError:
            if is_cma():
                raise MKUserError(
                    varprefix,
                    _("Failed to write to the configured directory. The target directory needs "
                      "to be writable."))
            else:
                raise MKUserError(
                    varprefix,
                    _("Failed to write to the configured directory. The site user needs to be able to "
                      "write the target directory. The recommended way is to make it writable by the "
                      "group \"omd\"."))

    # TODO: Duplicate code with mkbackup
    def backups(self):
        backups = {}

        self.verify_target_is_ready()

        for path in glob.glob("%s/*/mkbackup.info" % self._params["path"]):
            try:
                info = self._load_backup_info(path)
            except IOError as e:
                if e.errno == errno.EACCES:
                    continue  # Silently skip not permitted files
                raise

            backups[info["backup_id"]] = info

        return backups

    # TODO: Duplocate code with mkbackup
    def verify_target_is_ready(self):
        if self._params["is_mountpoint"] and not os.path.ismount(self._params["path"]):
            raise MKGeneralException("The backup target path is configured to be a mountpoint, "
                                     "but nothing is mounted.")

    # TODO: Duplicate code with mkbackup
    def _load_backup_info(self, path):
        info = json.load(open(path))

        # Load the backup_id from the second right path component. This is the
        # base directory of the mkbackup.info file. The user might have moved
        # the directory, e.g. for having multiple backups. Allow that.
        # Maybe we need to changed this later when we allow multiple generations
        # of backups.
        info["backup_id"] = os.path.basename(os.path.dirname(path))

        return info

    def get_backup(self, backup_ident):
        backups = self.backups()
        return backups[backup_ident]

    def remove_backup(self, backup_ident):
        self.verify_target_is_ready()
        shutil.rmtree("%s/%s" % (self._params["path"], backup_ident))


#.
#   .--Key Management------------------------------------------------------.
#   |             _  __            __  __                 _                |
#   |            | |/ /___ _   _  |  \/  | __ _ _ __ ___ | |_              |
#   |            | ' // _ \ | | | | |\/| |/ _` | '_ ` _ \| __|             |
#   |            | . \  __/ |_| | | |  | | (_| | | | | | | |_              |
#   |            |_|\_\___|\__, | |_|  |_|\__, |_| |_| |_|\__|             |
#   |                      |___/          |___/                            |
#   +----------------------------------------------------------------------+
#   | Managing of the keys that are used for signing the agents            |
#   '----------------------------------------------------------------------'


class BackupKeypairStore(key_mgmt.KeypairStore):
    pass


class PageBackupKeyManagement(key_mgmt.PageKeyManagement):
    edit_mode = "backup_edit_key"
    upload_mode = "backup_upload_key"
    download_mode = "backup_download_key"

    def jobs(self):
        raise NotImplementedError()

    def title(self):
        return _("Keys for backups")

    def page(self):
        show_key_download_warning(self.keys)
        super(PageBackupKeyManagement, self).page()

    def _back_button(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup")]), "back")

    def _key_in_use(self, key_id, key):
        for job in self.jobs().objects.itervalues():
            job_key_id = job.key_ident()
            if job_key_id is not None and key_id == job_key_id:
                return True
        return False

    def _table_title(self):
        return self.title()

    def _delete_confirm_msg(self):
        return _("Are you sure you want to delete this key?<br><br>"
                 "<b>Beware:</b> Deleting this key "
                 "means that you will not be able to encrypt or sign backups with the key. "
                 "Already created backups which have been encrypted, can not be decrypted "
                 "without access to this key. So please be sure that you either have a "
                 "backup or don't need this key anymore.")


class PageBackupEditKey(key_mgmt.PageEditKey):
    back_mode = "backup_keys"

    def title(self):
        return _("Create backup key")

    def _passphrase_help(self):
        return _("The backup key will be stored encrypted using this passphrase on your "
                 "disk. The passphrase will not be stored anywhere. The backup will use "
                 "the public key part of the key to sign or encrypt the backups. If you "
                 "encrypt a backup, you will need the private key part together with the "
                 "passphrase to decrypt the backup.")

    def _generate_key(self, alias, passphrase):
        key = super(PageBackupEditKey, self)._generate_key(alias, passphrase)
        # Mark key as not downloaded yet to issue a warning to the user that the key
        # should be backed up. The warning is removed on first download.
        key["not_downloaded"] = True
        return key


class PageBackupUploadKey(key_mgmt.PageUploadKey):
    back_mode = "backup_keys"

    def title(self):
        return _("Upload backup key")

    def _passphrase_help(self):
        return _("The backup key will be stored encrypted using this passphrase on your "
                 "disk. The passphrase will not be stored anywhere. The backup will use "
                 "the public key part of the key to sign or encrypt the backups. If you "
                 "encrypt a backup, you will need the private key part together with the "
                 "passphrase to decrypt the backup.")


class PageBackupDownloadKey(key_mgmt.PageDownloadKey):
    back_mode = "backup_keys"

    def title(self):
        return _("Download backup key")

    def _send_download(self, keys, key_id):
        super(PageBackupDownloadKey, self)._send_download(keys, key_id)
        if "not_downloaded" in keys[key_id]:
            del keys[key_id]["not_downloaded"]
        self.save(keys)

    def _file_name(self, key_id, key):
        raise NotImplementedError()


def show_key_download_warning(keys):
    to_load = [k["alias"] for k in keys.values() if "not_downloaded" in k]
    if to_load:
        html.show_warning(
            _("To be able to restore your encrypted backups, you need to "
              "download and keep the backup encryption keys in a safe place. "
              "If you loose your keys or the keys passphrases, your backup "
              "can not be restored.<br>"
              "The following keys have not been downloaded yet: %s") % ", ".join(to_load))


#.
#   .--Restore-------------------------------------------------------------.
#   |                  ____           _                                    |
#   |                 |  _ \ ___  ___| |_ ___  _ __ ___                    |
#   |                 | |_) / _ \/ __| __/ _ \| '__/ _ \                   |
#   |                 |  _ <  __/\__ \ || (_) | | |  __/                   |
#   |                 |_| \_\___||___/\__\___/|_|  \___|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Listing backups of targets and controlling the the restore procedure |
#   '----------------------------------------------------------------------'


class RestoreJob(MKBackupJob):
    def __init__(self, target_ident, backup_ident, passphrase=None):
        super(RestoreJob, self).__init__()
        self._target_ident = target_ident
        self._backup_ident = backup_ident
        self._passphrase = passphrase

    def title(self):
        return _("Restore")

    def state_file_path(self):
        if not is_site():
            return "/var/lib/mkbackup/restore.state"
        return "/tmp/restore-%s.state" % os.environ["OMD_SITE"]

    def complete(self):
        self.cleanup()

    def _start_command(self):
        return [mkbackup_path(), "restore", "--background", self._target_ident, self._backup_ident]

    def start(self, env=None):
        if self._passphrase is not None:
            if env is None:
                env = {}
            env.update(os.environ.copy())
            env["MKBACKUP_PASSPHRASE"] = self._passphrase
        super(RestoreJob, self).start(env)


class PageBackupRestore(object):
    def __init__(self):
        self._load_target()
        super(PageBackupRestore, self).__init__()

    def keys(self):
        raise NotImplementedError()

    def _load_target(self):
        ident = html.request.var("target")
        if ident is None:
            self._target_ident = None
            self._target = None
            return

        self._target_ident = ident

        try:
            self._target = self._get_target(self._target_ident)
        except KeyError:
            raise MKUserError("target_p_target", _("This backup target does not exist."))

    def _get_target(self, target_ident):
        return self.targets().get(target_ident)

    def title(self):
        raise NotImplementedError()

    def targets(self):
        raise NotImplementedError()

    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup")]), "back")
        if self._restore_is_running():
            html.context_button(_("Stop"), html.makeactionuri([("_action", "stop")]),
                                "backup_restore_stop")

        elif self._restore_was_started():
            html.context_button(_("Complete the restore"),
                                html.makeactionuri([("_action", "complete")]),
                                "backup_restore_complete")

    def action(self):
        action = html.request.var("_action")
        backup_ident = html.request.var("_backup")

        if action is None:
            return  # Only choosen the target

        if not html.transaction_valid():
            return

        if action == "delete":
            return self._delete_backup(backup_ident)

        elif action == "complete":
            return self._complete_restore(backup_ident)

        elif action == "start":
            return self._start_restore(backup_ident)

        elif action == "stop":
            return self._stop_restore(backup_ident)

        else:
            raise NotImplementedError()

    def _delete_backup(self, backup_ident):
        if self._restore_is_running():
            raise MKUserError(
                None,
                _("A restore is currently running. You can only delete "
                  "backups while no restore is running."))

        if backup_ident not in self._target.backups():
            raise MKUserError(None, _("This backup does not exist."))

        confirm = html.confirm(_("Do you really want to delete this backup?"),
                               add_header=self.title(),
                               method="GET")

        if confirm is False:
            return False

        elif confirm:
            html.check_transaction()  # invalidate transid
            self._target.remove_backup(backup_ident)
            return None, _("The backup has been deleted.")

    def _restore_was_started(self):
        return RestoreJob(self._target_ident, None).was_started()

    def _restore_is_running(self):
        return RestoreJob(self._target_ident, None).is_running()

    def _start_restore(self, backup_ident):
        backup_info = self._target.get_backup(backup_ident)
        if backup_info["config"]["encrypt"] is not None:
            return self._start_encrypted_restore(backup_ident, backup_info)
        return self._start_unencrypted_restore(backup_ident)

    def _complete_restore(self, backup_ident):
        RestoreJob(self._target_ident, None).complete()

    def _start_encrypted_restore(self, backup_ident, backup_info):
        key_digest = backup_info["config"]["encrypt"]

        try:
            _key_id, key = self.keys().get_key_by_digest(key_digest)
        except KeyError:
            raise MKUserError(
                None,
                _("The key with the fingerprint %s which is needed to decrypt "
                  "the backup is misssing.") % key_digest)

        if html.form_submitted("key"):
            try:
                value = self._vs_key().from_html_vars("_key")
                if html.request.has_var("_key_p_passphrase"):
                    self._vs_key().validate_value(value, "_key")
                    passphrase = value["passphrase"]

                    # Validate the passphrase
                    key_mgmt.decrypt_private_key(key["private_key"], passphrase)

                    html.check_transaction()  # invalidate transid
                    RestoreJob(self._target_ident, backup_ident, passphrase).start()
                    return None, _("The restore has been started.")
            except MKUserError as e:
                html.add_user_error(e.varname, e)

        # Special handling for Check_MK / CMA differences
        if is_site():
            html.header(_("Insert passphrase"))
            html.begin_context_buttons()
            html.context_button(_("Back"), html.makeuri([("mode", "backup_restore")]), "back")
            html.end_context_buttons()

        html.show_user_errors()
        html.p(
            _("To be able to decrypt and restore the encrypted backup, you need to enter the "
              "passphrase of the encryption key."))
        html.begin_form("key", method="GET")
        html.hidden_field("_action", "start")
        html.hidden_field("_backup", backup_ident)
        html.prevent_password_auto_completion()
        self._vs_key().render_input("_key", {})
        html.button("upload", _("Start restore"))
        self._vs_key().set_focus("_key")
        html.hidden_fields()
        html.end_form()
        html.footer()
        return False

    def _vs_key(self):
        return Dictionary(
            title=_("Properties"),
            elements=[
                ("passphrase",
                 Password(
                     title=_("Passphrase"),
                     allow_empty=False,
                     is_stored_plain=False,
                 )),
            ],
            optional_keys=False,
            render="form",
        )

    def _start_unencrypted_restore(self, backup_ident):
        confirm = html.confirm(_("Do you really want to start the restore of this backup?"),
                               add_header=self.title(),
                               method="GET")
        if confirm is False:
            return False

        elif confirm:
            html.check_transaction()  # invalidate transid
            RestoreJob(self._target_ident, backup_ident).start()
            return None, _("The restore has been started.")

    def _stop_restore(self, backup_ident):
        confirm = html.confirm(_("Do you really want to stop the restore of this backup? This will "
                                 "leave your environment in an undefined state."),
                               add_header=self.title(),
                               method="GET")

        if confirm is False:
            return False

        elif confirm:
            html.check_transaction()  # invalidate transid
            RestoreJob(self._target_ident, backup_ident).stop()
            return None, _("The restore has been stopped.")

    def page(self):
        if self._restore_was_started():
            self._show_restore_progress()

        elif self._target:
            self._show_backup_list()

        else:
            self._show_target_list()

    def _show_target_list(self):
        html.p(_("Please choose a target to perform the restore from."))
        self.targets().show_list()

    def _show_backup_list(self):
        raise NotImplementedError()

    def _show_restore_progress(self):
        PageBackupRestoreState().page()


class PageBackupRestoreState(PageAbstractBackupJobState):
    def __init__(self):
        super(PageBackupRestoreState, self).__init__()
        self._job = RestoreJob(None, None)  # TODO: target_ident and backup_ident needed?
        self._ident = "restore"
