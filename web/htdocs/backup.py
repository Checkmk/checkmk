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

import os
import pprint
import signal
import socket
import subprocess

import defaults
import table
from valuespec import *
from lib import write_settings_file, age_human_readable, MKUserError
import cmk.render as render

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

g_var_path = "/var/lib/mkbackup"

def mkbackup_path():
    if "OMD_ROOT" not in os.environ:
        return "/usr/sbin/mkbackup"
    else:
        return "%s/bin/mkbackup" % os.environ["OMD_ROOT"]


def system_config_path():
    return "/etc/cma/backup.conf"


def site_config_path():
    if "OMD_ROOT" not in os.environ:
	raise Exception(_("Not executed in OMD environment!"))
    return "%s/etc/check_mk/backup.mk" % os.environ["OMD_ROOT"]


def hostname():
    return socket.gethostname()


def is_cma():
    return os.path.exists("/etc/cma/cma.conf")


# TODO: Locking!
class Config(object):
    def __init__(self, file_path):
        self._file_path = file_path


    def load(self):
        if not os.path.exists(self._file_path):
            return {
                "targets" : {},
                "jobs"    : {},
            }

        return eval(file(self._file_path).read())


    def save(self, config):
        write_settings_file(self._file_path, config)


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
        self._ident  = ident
        self._config = {}

        self.from_config(config)


    def ident(self):
        return self._ident


    def title(self):
        return self._config["title"]


    def to_config(self):
        return self._config


    def from_config(self, config):
        self._config = config



class BackupEntityCollection(object):
    def __init__(self, config_file_path, cls, config_attr):
        self._config_path = config_file_path
        self._config      = Config(config_file_path).load()
        self._cls         = cls
        self._config_attr = config_attr
        self.objects = dict([ (ident, cls(ident, config))
                              for ident, config
                              in self._config[config_attr].items() ])


    def get(self, ident):
        return self.objects[ident]


    def remove(self, obj):
        try:
            del self.objects[obj.ident()]
        except KeyError:
            pass


    def choices(self):
        return sorted([ (ident, obj.title()) for ident, obj in self.objects.items() ],
                        key=lambda (x, y): y.title())


    def add(self, obj):
        self.objects[obj.ident()] = obj


    def save(self):
        self._config[self._config_attr] = dict([ (ident, obj.to_config())
                                           for ident, obj in self.objects.items() ])
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


class Job(BackupEntity):
    @classmethod
    def state_name(self, state):
        return {
            "started"  : _("Started"),
            "running"  : _("Currently running"),
            "finished" : _("Ended"),
            None       : _("Never executed"),
        }[state]


    def target_ident(self):
        return self._config["target"]


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

        return "-".join([ p.replace("-", "+") for p in parts ])


    def state_file_path(self):
        return "%s/%s.state" % (g_var_path, self.global_ident())


    def state(self):
        try:
            state = eval(file(self.state_file_path()).read())
        except IOError, e:
            if e.errno == 2: # not existant
                state = {
                    "state"   : None,
                    "started" : None,
                    "output"  : "",
                }
            else:
                raise
        except Exception, e:
            raise MKGeneralException(_("Failed to parse state file \"%s\": %s" %
                                        (self.state_file_path(), e)))

        # Fix data structure when the process has been killed
        if state["state"] == "running" and not os.path.exists("/proc/%d" % state["pid"]):
            state.update({
                "state"    : "finished",
                "finished" : max(state["started"], os.stat(self.state_file_path()).st_mtime),
                "success"  : False,
            })

        return state


    def is_running(self):
        if not os.path.exists(self.state_file_path()):
            return False

        state = self.state()
        return state["state"] in [ "started", "running" ] \
               and os.path.exists("/proc/%d" % state["pid"])


    def start(self):
        p = subprocess.Popen([mkbackup_path(), "backup", "--background", self.ident()],
                         shell=False, close_fds=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, stdin=open(os.devnull))
        if p.wait() != 0:
            raise MKGeneralException(_("Failed to start the backup: %s") % p.stdout.read())


    def stop(self):
        state = self.state()
        pgid = os.getpgid(state["pid"])

        try:
            os.killpg(pgid, signal.SIGTERM)
        except OSError, e:
            if e.errno == 3:
                pass
            else:
                raise

        wait = 5 # sec
        while os.path.exists("/proc/%d" % state["pid"]) and wait > 0:
            time.sleep(0.5)
            wait -= 0.5

        # When still running after 5 seconds, enforce
        if wait == 0:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except OSError, e:
                if e.errno == 3:
                    pass
                else:
                    raise



class Jobs(BackupEntityCollection):
    def __init__(self, config_file_path):
        super(Jobs, self).__init__(config_file_path, cls=Job, config_attr="jobs")


    def show_list(self):
        html.write("<h2>%s</h2>" % _("Jobs"))
        table.begin(sortable=False, searchable=False)

        for job_ident, job in sorted(self.objects.items()):
            table.row()
            table.cell(_("Actions"), css="buttons")
            delete_url = html.makeactionuri_contextless(
                            [("mode", "backup"), ("_action", "delete"), ("_job", job_ident)])
            edit_url   = html.makeuri_contextless(
                            [("mode", "edit_backup_job"), ("job", job_ident)])
            state_url  = html.makeuri_contextless(
                            [("mode", "backup_job_state"), ("job", job_ident)])

            state = job.state()

            if not job.is_running():
                html.icon_button(edit_url, _("Edit this backup job"), "edit")
                html.icon_button(delete_url, _("Delete this backup job"), "delete")

            if state["state"] != None:
                html.icon_button(state_url, _("Show current / last state of this backup job"),
                                 "backup_state")

            if not job.is_running():
                start_url = html.makeactionuri_contextless(
                            [("mode", "backup"), ("_action", "start"), ("_job", job_ident)])

                html.icon_button(start_url, _("Manually start this backup"), "backup_start")
            else:
                stop_url = html.makeactionuri_contextless(
                            [("mode", "backup"), ("_action", "stop"), ("_job", job_ident)])

                html.icon_button(stop_url, _("Stop this backup job"), "backup_stop")

            table.cell(_("Name"), html.attrencode(job.title()))

            css = "state0"
            if state["state"] == "finished" and not state["success"]:
                css = "state2"

            table.cell(_("State"), css=css)
            html.write(html.attrencode(job.state_name(state["state"])))

            table.cell(_("Runtime"))
            if state["started"]:
                html.write(_("Started at %s") % render.date_and_time(state["started"]))
                duration = time.time() - state["started"]
                if state["state"] == "finished":
                    html.write(", Finished at %s" % render.date_and_time(state["started"]))
                    duration = state["finished"] - state["started"]

                html.write(_(" (Duration: %s, IO: %s/s)") % (age_human_readable(duration),
                                                 render.bytes(state["bytes_per_second"])))

            # TODO: Render schedule
            #job_html = SchedulePeriod().value_to_text(job._config["period"]) \
            #                + _(" at ") \
            #                + ListOf(Timeofday()).value_to_text(job._config["timeofday"])
            #table.cell(_("job"), job_html)

        table.end()



class PageBackup(object):
    def __init__(self):
        super(PageBackup, self).__init__()


    def title(self):
        raise NotImplementedError()


    def jobs(self):
        raise NotImplementedError()


    def home_button(self):
        raise NotImplementedError()


    def buttons(self):
        self.home_button()
        html.context_button(_("Backup targets"), html.makeuri_contextless([("mode", "backup_targets")]), "backup_targets")
        html.context_button(_("New job"), html.makeuri_contextless([("mode", "edit_backup_job")]), "backup_job_new")


    def action(self):
        ident = html.var("_job")
        jobs = self.jobs()
        try:
            job = jobs.get(ident)
        except KeyError:
            raise MKUserError("_job", _("This backup job does not exist."))

        action = html.var("_action")

        if action == "delete":
            if not html.transaction_valid():
                return
        else:
            if not html.check_transaction():
                return

        if action == "delete":
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

        if html.confirm(_("Do you really want to delete this job?"),
                        add_header=self.title()):
            html.check_transaction() # invalidate transid
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
        self.jobs().show_list()



class PageEditBackupJob(object):
    def __init__(self):
        super(PageEditBackupJob, self).__init__()
        job_ident = html.var("job")

        if job_ident != None:
            try:
                job = self.jobs().get(job_ident)
            except KeyError:
                raise MKUserError("target", _("This backup job does not exist."))

            if job.is_running():
                raise MKUserError("_job", _("This job is currently running."))

            self._new          = False
            self._ident        = job_ident
            self._job_cfg      = job.to_config()
            self._title        = _("Edit backup job: %s") % job.title()
        else:
            self._new        = True
            self._ident      = None
            self._job_cfg    = {}
            self._title      = _("New backup job")


    def jobs(self):
        raise NotImplementedError()


    def targets(self):
        raise NotImplementedError()


    def title(self):
        return self._title


    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup")]), "back")


    def vs_backup_schedule(self):
        return Alternative(
            title = _("Schedule"),
            style = "dropdown",
            elements = [
                FixedValue(None,
                    title = _("Execute manually"),
                    totext = _("Only execute manually"),
                ),
                Dictionary(
                    title = _("Schedule execution"),
                    elements = [
                        ("period", SchedulePeriod()),
                        ("timeofday", ListOf(
                            Timeofday(
                                default_value = (0, 0),
                            ),
                            title = _("Time of day to start the backup at"),
                            movable = False,
                            default_value = [(0, 0)],
                            add_label = _("Add new time"),
                            empty_text = _("Please specify at least one time."),
                            allow_empty = False,
                        )),
                    ],
                ),
            ]
        )


    def vs_backup_job(self):
        if self._new:
            ident_attr = [
                ("ident", ID(
                    title = _("Unique ID"),
                    help = _("The ID of the job must be a unique text. It will be used as an internal key "
                             "when objects refer to the job."),
                    allow_empty = False,
                    size = 12,
                    validate = self._validate_backup_job_ident,
                )),
            ]
        else:
            ident_attr = []


        return Dictionary(
            title = _("Backup job"),
            elements = ident_attr + [
                ("title", TextUnicode(
                    title = _("Title"),
                    allow_empty = False,
                )),
                ("target", DropdownChoice(
                    title = _("Target"),
                    choices = self.backup_target_choices,
                    validate = self._validate_target,
                )),
                ("schedule", self.vs_backup_schedule()),
            ] + self.custom_job_attributes(),
        optional_keys = [],
        render = "form",
    )


    # Can be overridden by subclasses to add custom attributes to the
    # job configuration. e.g. system jobs can exclude sites optionally.
    def custom_job_attributes(self):
        return []


    def _validate_backup_job_ident(self, value, varprefix):
        if value in self.jobs().objects:
            raise MKUserError(varprefix, _("This ID is already used by another backup job."))


    def _validate_target(self, value, varprefix):
        target = self.targets().get(value)
        if target.type_ident() != "local":
            raise NotImplementedError()

        path = target.type_params()["path"]
        target.type_class()().validate_local_directory(path, varprefix)


    def backup_target_choices(self):
        return sorted(self.targets().choices(), key=lambda (x, y): y.title())


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
        html.http_redirect(html.makeuri_contextless([("mode", "backup")]))


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



class PageBackupJobState(object):
    def __init__(self):
        super(PageBackupJobState, self).__init__()
        job_ident = html.var("job")
        if job_ident != None:
            try:
                self._job = self.jobs().get(job_ident)
            except KeyError:
                raise MKUserError("job", _("This backup job does not exist."))

            self._ident = job_ident
        else:
            raise MKUserError("job", _("You need to specify a backup job."))


    def jobs(self):
        raise NotImplementedError()


    def title(self):
        return _("Job state: %s") % self._job.title()


    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup")]), "back")


    def page(self):
        job   = self._job
        state = job.state()

        html.write("<table class=\"data backup_job\">")
        state_num = 0
        if state["state"] == "finished" and not state["success"]:
            state_num = 2
        html.write("<tr class=\"data even0\"><td class=\"left legend\">%s</td>" % _("State"))
        html.write("<td class=\"state state%d\">%s</td></tr>" %
                    (state_num, html.attrencode(job.state_name(state["state"]))))

        html.write("<tr class=\"data odd0\"><td class=\"left\">%s</td>" % _("Runtime"))
        html.write("<td>")
        if state["started"]:
            html.write(_("Started at %s") % render.date_and_time(state["started"]))
            duration = time.time() - state["started"]
            if state["state"] == "finished":
                html.write(", Finished at %s" % render.date_and_time(state["started"]))
                duration = state["finished"] - state["started"]

            html.write(_(" (Duration: %s)") % age_human_readable(duration))
        html.write("</td></tr>")

        html.write("<tr class=\"data even0\"><td class=\"left legend\">%s</td>" % _("Output"))
        html.write("<td class=\"log\"><pre>%s</pre></td></tr>" % html.attrencode(state["output"]))

        html.write("</table>")



class SystemBackupJobs(Jobs):
    def __init__(self):
        super(SystemBackupJobs, self).__init__(system_config_path())

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
        return BackupTargetType.get_type(self.type_ident())


    def type_params(self):
        return self._config["remote"][1]



class Targets(BackupEntityCollection):
    def __init__(self, config_file_path):
        super(Targets, self).__init__(config_file_path, cls=Target, config_attr="targets")


    def show_list(self, title=None, editable=True):
        title = title if title else _("Targets")
        html.write("<h2>%s</h2>" % title)
        if not editable:
            html.write("<p>%s</p>" % _("These backup targets can not be edited here. You need to "
                                       "open the device backup management."))

        table.begin(sortable=False, searchable=False)

        for target_ident, target in sorted(self.objects.items()):
            table.row()
            if editable:
                table.cell(_("Actions"), css="buttons")
                delete_url = html.makeactionuri_contextless(
                                [("mode", "backup_targets"), ("target", target_ident)])
                edit_url = html.makeuri_contextless(
                                [("mode", "edit_backup_target"), ("target", target_ident)])

                html.icon_button(edit_url, _("Edit this backup target"), "edit")
                html.icon_button(delete_url, _("Delete this backup target"), "delete")

            table.cell(_("Title"), html.attrencode(target.title()))

            vs_target = target.type_class()().valuespec()
            table.cell(_("Destination"), vs_target.value_to_text(target.type_params()))

        table.end()



class PageBackupTargets(object):
    def __init__(self):
        super(PageBackupTargets, self).__init__()


    def title(self):
        raise NotImplementedError()


    def targets(self):
        raise NotImplementedError()


    def jobs(self):
        raise NotImplementedError()


    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup")]), "back")
        html.context_button(_("New backup target"), html.makeuri_contextless([
                                    ("mode", "edit_backup_target")]), "backup_target_edit")


    def action(self):
        if html.transaction_valid():
            ident = html.var("target")
            targets = self.targets()
            try:
                target = targets.get(ident)
            except KeyError:
                raise MKUserError("target", _("This backup target does not exist."))

            job_titles = [ j.title() for j in self._jobs_using_target(target) ]
            if job_titles:
                raise MKUserError("target", _("You can not delete this target because it is used "
                                              "by these backup jobs: %s") % ", ".join(job_titles))

            if html.confirm(_("Do you really want to delete this target?"),
                            add_header=self.title()):
                targets.remove(target)
                targets.save()
                return None, _("The target has been deleted.")


    def _jobs_using_target(self, target):
        jobs = []
        for job in self.jobs().objects.values():
            if job.target_ident() == target.ident():
                jobs.append(job)
        return jobs


    def page(self):
        self.targets().show_list()
        SystemBackupTargets().show_list(editable=False, title=_("System global targets"))



class PageEditBackupTarget(object):
    def __init__(self):
        super(PageEditBackupTarget, self).__init__()
        target_ident = html.var("target")

        if target_ident != None:
            try:
                target = self.targets().get(target_ident)
            except KeyError:
                raise MKUserError("target", _("This backup target does not exist."))

            self._new        = False
            self._ident      = target_ident
            self._target_cfg = target.to_config()
            self._title      = _("Edit backup target: %s") % target.title()
        else:
            self._new        = True
            self._ident      = None
            self._target_cfg = {}
            self._title      = _("New backup target")


    def targets(self):
        raise NotImplementedError()


    def title(self):
        return self._title


    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "backup_targets")]), "back")


    def vs_backup_target(self):
        if self._new:
            ident_attr = [
                ("ident", ID(
                    title = _("Unique ID"),
                    help = _("The ID of the target must be a unique text. It will be used as an internal key "
                             "when objects refer to the target."),
                    allow_empty = False,
                    size = 12,
                    validate = self.validate_backup_target_ident,
                )),
            ]
        else:
            ident_attr = []


        return Dictionary(
            title = _("Backup target"),
            elements = ident_attr + [
                ("title", TextUnicode(
                    title = _("Title"),
                    allow_empty = False,
                )),
                ("remote", CascadingDropdown(
                    title = _("Destination"),
                    choices = BackupTargetType.choices,
                )),
            ],
            optional_keys = [],
            render = "form",
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
        html.http_redirect(html.makeuri_contextless([("mode", "backup_targets")]))


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



class SystemBackupTargets(Targets):
    def __init__(self):
        super(SystemBackupTargets, self).__init__(system_config_path())


    def show_list(self, *args, **kwargs):
        if is_cma():
            super(SystemBackupTargets, self).show_list(*args, **kwargs)


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


class BackupTargetType(object):
    ident = None

    @classmethod
    def choices(cls):
        choices = []
        for type_class in cls.__subclasses__():
            choices.append((type_class.ident, type_class.title(), type_class().valuespec()))
        return sorted(choices, key=lambda x: x[1])


    @classmethod
    def get_type(cls, type_ident):
        for type_class in cls.__subclasses__():
            if type_class.ident == type_ident:
                return type_class


    @classmethod
    def title(cls):
        raise NotImplementedError()


    def __init__(self):
        pass


    def valuespec(self):
        raise NotImplementedError()



class BackupTargetLocal(BackupTargetType):
    ident = "local"

    @classmethod
    def title(cls):
        return _("Local path")


    def valuespec(self):
        return Dictionary(
            elements = [
                ("path", AbsoluteDirname(
                    title = _("Directory to save the backup to"),
                    help = _("This can be a local directory of your choice. You can also use this "
                             "option if you want to save your backup to a network share using "
                             "NFS, Samba or similar. But you will have to care about mounting the "
                             "network share on your own."),
                    allow_empty = False,
                    validate = self.validate_local_directory,
                )),
            ],
            optional_keys = [],
        )


    def validate_local_directory(self, value, varprefix):
        if is_cma() and not value.startswith("/mnt/"):
            raise MKUserError(varprefix, _("You can only use mountpoints below the <tt>/mnt</tt> "
                                           "directory as backup targets."))

        if not os.path.isdir(value):
            raise MKUserError(varprefix, _("The path does not exist or is not a directory. You "
                                           "need to specify an already existing directory."))

        # Check write access for the site user
        test_file_path = os.tempnam(value, "write_test")
        try:
            file(test_file_path, "w")
            os.unlink(test_file_path)
        except IOError, e:
            raise MKUserError(varprefix,
                _("Failed to write to the configured directory. The site user needs to be able to "
                  "write the target directory. The recommended way is to make it writable by the "
                  "group \"omd\"."))
