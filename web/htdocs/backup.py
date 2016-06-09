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

import defaults
import table
from valuespec import *
from lib import write_settings_file

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
                "targets"   : {},
                "schedules" : {},
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
#   .--Schedules-----------------------------------------------------------.
#   |            ____       _              _       _                       |
#   |           / ___|  ___| |__   ___  __| |_   _| | ___  ___             |
#   |           \___ \ / __| '_ \ / _ \/ _` | | | | |/ _ \/ __|            |
#   |            ___) | (__| | | |  __/ (_| | |_| | |  __/\__ \            |
#   |           |____/ \___|_| |_|\___|\__,_|\__,_|_|\___||___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Backup schedule handling. A schedule is a single backup job which    |
#   | runs in the configured interval and saves the backup to the choosen  |
#   | backup target.                                                       |
#   '----------------------------------------------------------------------'


class Schedule(BackupEntity):
    pass


class Schedules(BackupEntityCollection):
    def __init__(self, config_file_path):
        super(Schedules, self).__init__(config_file_path, cls=Schedule, config_attr="schedules")


    def show_list(self):
        html.write("<h2>%s</h2>" % _("Schedules"))
        table.begin(sortable=False, searchable=False)

        for schedule_ident, schedule in sorted(self.objects.items()):
            table.row()
            table.cell(_("Actions"), css="buttons")
            delete_url = html.makeactionuri_contextless(
                            [("mode", "backup"), ("delete_schedule", schedule_ident)])
            edit_url = html.makeuri_contextless(
                            [("mode", "edit_backup_schedule"), ("schedule", schedule_ident)])

            html.icon_button(edit_url, _("Edit this backup schedule"), "edit")
            html.icon_button(delete_url, _("Delete this backup schedule"), "delete")

            table.cell(_("Name"),     html.attrencode(schedule.title()))
            schedule_html = SchedulePeriod().value_to_text(schedule._config["period"]) \
                            + _(" at ") \
                            + ListOf(Timeofday()).value_to_text(schedule._config["timeofday"])
            table.cell(_("Schedule"), schedule_html)

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
    pass


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
            # TODO: Destination to_text

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
        for cls in cls.__subclasses__():
            choices.append((cls.ident, cls.title(), cls().valuespec()))
        return sorted(choices, key=lambda x: x[1])


    @classmethod
    def title(cls):
        raise NotImplementedError()


    def __init__(self):
        pass


    def valuespec(self):
        raise NotImplementedError()



class BackupTargetNFS(BackupTargetType):
    ident = "nfs"

    @classmethod
    def title(cls):
        return _("Network: NFS")


    def valuespec(self):
        return Dictionary(
            elements = [
                ("share", Tuple(
                    title = _("NFS share"),
                    elements = [
                        Hostname(
                            title = _("Host address"),
                            help = _("The host address (name or IP address) to reach the NFS server.")
                        ),
                        AbsoluteDirname(
                            title = _("Share path"),
                            help = _("The export path used to mount the share.")
                        ),
                    ],
                    orientation = "horizontal",
                )),
                ("mount_options", ListOfStrings(
                    title = _("Mount options"),
                    help = _("Options to be used when mounting the NFS share."),
                    default_value = ["user", "noatime"],
                    orientation = "horizontal",
                )),
            ],
            optional_keys = [],
        )



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
                    allow_empty = False,
                )),
            ],
            optional_keys = [],
        )



class BackupTargetSSH(BackupTargetType):
    ident = "ssh"

    @classmethod
    def title(cls):
        return _("Network: SSH (SCP/SFTP)")


    def valuespec(self):
        return Dictionary(
            # TODO
            elements = [
            ],
            optional_keys = [],
        )
