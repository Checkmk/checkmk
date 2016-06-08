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

import pprint

import defaults
import table

class BackupConfig(object):
    def __init__(self, path):
        self._path = path

        self.schedules = {}
        self.targets   = {}


    def load(self):
        if not os.path.exists(self._path):
            return

        cfg = {
            "schedules" : {},
            "targets"   : {},
        }
        execfile(filename, cfg, cfg)

        self.schedules = cfg["schedules"]
        self.targets   = cfg["targets"]


    def save(self):
        with create_user_file(path, "w") as f:
            f.write("schedules = \\\n%s\n" % pprint.pformat(self.schedules))
            f.write("targets  = \\\n%s\n" % pprint.pformat(self.schedules))



class Schedule(object):
    def __init__(self):
        self.name = "XXX"



class Schedules(object):
    def __init__(self, config_file_path):
        self._config = BackupConfig(config_file_path)
        self.schedules = dict([ (ident, Schedule(ident, config))
                                for ident, config in self._config.schedules.items() ])


    def show_list(self):
        html.write("<h2>%s</h2>" % _("Schedules"))
        table.begin(sortable=False, searchable=False)

        for schedule in sorted(self.schedules.items()):
            table.row()
            for cell in row:
                table.cell(_("Name"), html.attrencode(schedule.name))

        table.end()



class Target(object):
    def __init__(self, ident, config):
        self._ident = ident
        self.title  = None

        self.from_config(config)


    def to_config(self):
        return self._config


    def from_config(self, config):
        for k, v in config.items():
            if hasattr(self, k):
                setattr(self, k, v)



class Targets(object):
    def __init__(self, config_file_path):
        self._config = BackupConfig(config_file_path)
        self.targets = dict([ (ident, Target(ident, config))
                              for ident, config in self._config.targets.items() ])


    def get(self, ident):
        return self.targets[ident]


    def show_list(self, title=None, editable=False):
        title = title if title else _("Targets")
        html.write("<h2>%s</h2>" % title)
        table.begin(sortable=False, searchable=False)

        for target in sorted(self.targets.items()):
            table.row()
            for cell in row:
                # Buttons: editable True/False
                table.cell(_("Title"), html.attrencode(target.title))

        table.end()
