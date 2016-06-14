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
import subprocess

import defaults
import table
from valuespec import *
from lib import write_settings_file, age_human_readable

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


    def remove(self, ident):
        try:
            del self.objects[ident]
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
        }[state]


    # TODO: Duplicated code with mkbackup
    def ident(self):
        site_id = defaults.omd_site
        if site_id:
            return "site-%s-%s" % (site_id, self._ident)
        else:
            return "system-%s" % (self._ident)


    def state_file_path(self):
        return "%s/%s.state" % (g_var_path, self.ident())


    def state(self):
        state = eval(file(self.state_file_path()).read())

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
        p = subprocess.Popen([mkbackup_path(), "backup", "--background", self._ident],
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

        def fmt_datetime(t):
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))

        for job_ident, job in sorted(self.objects.items()):
            table.row()
            table.cell(_("Actions"), css="buttons")
            delete_url = html.makeactionuri_contextless(
                            [("mode", "backup"), ("_action", "delete"), ("_job", job_ident)])
            edit_url   = html.makeuri_contextless(
                            [("mode", "edit_backup_job"), ("job", job_ident)])
            state_url  = html.makeuri_contextless(
                            [("mode", "backup_job_state"), ("job", job_ident)])

            if not job.is_running():
                html.icon_button(edit_url, _("Edit this backup job"), "edit")
                html.icon_button(delete_url, _("Delete this backup job"), "delete")

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

            state = job.state()

            css = "state0"
            if state["state"] == "finished" and not state["success"]:
                css = "state2"

            table.cell(_("State"), css=css)
            html.write(html.attrencode(job.state_name(state["state"])))

            table.cell(_("Runtime"))
            html.write(_("Started at %s") % fmt_datetime(state["started"]))
            duration = time.time() - state["started"]
            if state["state"] == "finished":
                html.write(", Finished at %s" % fmt_datetime(state["started"]))
                duration = state["finished"] - state["started"]

            html.write(_(" (Duration: %s)") % age_human_readable(duration))

            # TODO: Render schedule
            #job_html = SchedulePeriod().value_to_text(job._config["period"]) \
            #                + _(" at ") \
            #                + ListOf(Timeofday()).value_to_text(job._config["timeofday"])
            #table.cell(_("job"), job_html)

        table.end()


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


    def type_params(self):
        return self._config["remote"][1]



class Targets(BackupEntityCollection):
    def __init__(self, config_file_path):
        super(Targets, self).__init__(config_file_path, cls=Target, config_attr="targets")


    def show_list(self, title=None, editable=True):
        title = title if title else _("Targets")
        html.write("<h2>%s</h2>" % title)
        if not editable:
            html.write("<p>%s</p>" % _("These backup targets can not be edited here."))

        table.begin(sortable=False, searchable=False)

        for target_ident, target in sorted(self.objects.items()):
            table.row()
            table.cell(_("Actions"), css="buttons")
            if editable:
                delete_url = html.makeactionuri_contextless(
                                [("mode", "backup_targets"), ("target", target_ident)])
                edit_url = html.makeuri_contextless(
                                [("mode", "edit_backup_target"), ("target", target_ident)])

                html.icon_button(edit_url, _("Edit this backup target"), "edit")
                html.icon_button(delete_url, _("Delete this backup target"), "delete")

            table.cell(_("Title"), html.attrencode(target.title()))

            vs_target = BackupTargetType.get_type(target.type_ident())().valuespec()
            table.cell(_("Destination"), vs_target.value_to_text(target.type_params()))

        table.end()


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
                    validate = self._validate_local_directory,
                )),
            ],
            optional_keys = [],
        )


    def _validate_local_directory(self, value, varprefix):
        if not os.path.isdir(value):
            raise MKUserError(varprefix, _("The path does not exist or is not a directory. You "
                                           "need to specify an already existing directory."))
