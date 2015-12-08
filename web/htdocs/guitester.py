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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import defaults
from lib import *


class MKGuitestFailed(MKException):
    def __init__(self, errors):
        self.errors = errors
        MKException.__init__(self, _("GUI Test failed"))


class GUITester:
    def __init__(self):
        self.guitest = None
        self.replayed_guitest_step = None


    def init_guitests(self):
        if self.myfile == "guitest":
            self.replay_guitest()
        elif self.guitest_recording_active():
            self.begin_guitest_recording()


    def begin_guitest_recording(self):
        self.guitest = {
            "variables" : self.vars.copy(),
            "filename" : self.myfile,
            "output" : {},
        }
        # Fix transaction ID: We are just interested in whether it is valid or not
        if "_transid" in self.vars:
            if self.transaction_valid():
                self.guitest["variables"]["_transid"] = "valid"
            else:
                self.guitest["variables"]["_transid"] = "invalid"

        self.add_status_icon("guitest", _("GUI test recording is active"))


    def end_guitest_recording(self):
        if self.guitest != None:
            self.guitest["user"] = self.user
            self.guitest["elapsed_time"] = time.time() - self.start_time
            self.save_guitest_step(self.guitest)


    def save_guitest_step(self, step):
        path = defaults.var_dir + "/guitests/RECORD"
        if not os.path.exists(path):
            test_steps = []
        else:
            test_steps = eval(file(path).read())
        test_steps.append(step)
        file(path, "w").write("%s\n" % pprint.pformat(test_steps))


    def load_guitest(self, name):
        path = defaults.var_dir + "/guitests/" + name + ".mk"
        try:
            return eval(file(path).read())
        except IOError, e:
            raise MKGeneralException(_("Cannot load GUI test file %s: %s") % (self.attrencode(path), e))


    def replay_guitest(self):
        test_name = self.var("test")
        if not test_name:
            raise MKGuitestFailed([_("Missing the name of the GUI test to run (URL variable 'test')")])
        guitest = self.load_guitest(test_name)

        step_nr_text = self.var("step")
        try:
            step_nr = int(step_nr_text)
        except:
            raise MKGuitestFailed([_("Invalid or missing test step number (URL variable 'step')")])
        if step_nr >= len(guitest) or step_nr < 0:
            raise MKGuitestFailed([_("Invalid test step number %d (only 0...%d)") % (step_nr, len(guitest)-1)])

        self.replayed_guitest_step = guitest[step_nr]
        self.replayed_guitest_step["replay"] = {}
        self.myfile = self.replayed_guitest_step["filename"]
        self.guitest_fake_login(self.replayed_guitest_step["user"])
        self.vars = self.replayed_guitest_step["variables"]
        if "_transid" in self.vars and self.vars["_transid"] == "valid":
            self.vars["_transid"] = self.get_transid()
            self.store_new_transids()


    def end_guitest_replay(self):
        if self.replayed_guitest_step:
            errors = []
            for varname in self.replayed_guitest_step["output"].keys():
                errors += self.guitest_check_output(
                    varname,
                    self.replayed_guitest_step["output"][varname],
                    self.replayed_guitest_step["replay"].get(varname, []))
            if errors:
                raise MKGuitestFailed(errors)


    def guitest_check_output(self, varname, reference, reality):
        errors = []
        for entry in reference:
            if entry not in reality:
                errors.append("%s: missing entry %r" % (varname, entry))
        return errors


    def guitest_recording_active(self):
        # Activated by symoblic link pointing to recording file
        return os.path.lexists(defaults.var_dir + "/guitests/RECORD") and not \
           self.myfile in self.guitest_ignored_pages()


    def guitest_ignored_pages(self):
        return [ "run_cron", "index", "side", "sidebar_snapin", "dashboard", "dashboard_dashlet", "login" ]


    def guitest_record_output(self, key, value):
        if self.guitest:
            self.guitest["output"].setdefault(key, []).append(value)
        elif self.replayed_guitest_step:
            self.replayed_guitest_step["replay"].setdefault(key, []).append(value)


    def finalize_guitests(self):
        if self.guitest:
            self.end_guitest_recording()

        if self.replayed_guitest_step:
            try:
                self.end_guitest_replay()
            except MKGuitestFailed, e:
                self.write("\n[[[GUITEST FAILED]]]\n%s" % ("\n".join(e.errors)))
