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

import re
import time

import config
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
        self.guitest_repair_step = None


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

        self.add_status_icon("guitest", _("GUI test recording is active"))


    def end_guitest_recording(self):
        if self.guitest != None:
            self.guitest["user"] = self.user
            self.guitest["elapsed_time"] = time.time() - self.start_time
            self.save_guitest_step(self.guitest)


    # Is called whenever a valid transaction ID has been found
    def guitest_set_transid_valid(self):
        if self.guitest != None:
            self.guitest["variables"]["_transid"] = "valid"


    def save_guitest_step(self, step):
        path = defaults.var_dir + "/guitests/RECORD"
        if not os.path.exists(path):
            test_steps = []
        else:
            test_steps = eval(file(path).read())

        if self.guitest_repair_step != None:
            if self.guitest_repair_step > len(test_steps):
                raise MKGeneralException("Test step for repairing is %s, but test only has %d steps." %
                                          (self.guitest_repair_step, len(test_steps)))
            mod_step = test_steps[self.guitest_repair_step]
            mod_step["output"] = step["output"]
            mod_step["user"] = step["user"]
            mod_step["elapsed_time"] = step["elapsed_time"]
        else:
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

        repair = self.var("repair") == "1"
        if repair:
            self.guitest_repair_step = step_nr
            self.begin_guitest_recording()

        self.replayed_guitest_step = guitest[step_nr]
        self.replayed_guitest_step["replay"] = {}
        self.myfile = self.replayed_guitest_step["filename"]
        self.guitest_fake_login(self.replayed_guitest_step["user"])
        self.vars = self.replayed_guitest_step["variables"]
        if "_transid" in self.vars and self.vars["_transid"] == "valid":
            self.vars["_transid"] = self.get_transid()
            self.store_new_transids()


    def guitest_recording_active(self):
        # Activated by symoblic link pointing to recording file
        return os.path.lexists(defaults.var_dir + "/guitests/RECORD") and not \
           self.myfile in self.guitest_ignored_pages()


    def guitest_ignored_pages(self):
        return [ "run_cron", "index", "side", "sidebar_snapin", "sidebar_fold", "dashboard",
                 "dashboard_dashlet", "login", "logout", "tree_openclose", "ajax_switch_help" ]


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


    def end_guitest_replay(self):
        if self.replayed_guitest_step and self.guitest_repair_step == None:
            errors = []
            for varname in self.replayed_guitest_step["output"].keys():
                method = self.guitest_test_method(varname)
                errors_for_this_varname = method(
                                self.replayed_guitest_step["output"][varname],
                                self.replayed_guitest_step["replay"].get(varname, []))
                errors += [ "%s: %s" % (varname, error) for error in errors_for_this_varname ]
            if errors:
                raise MKGuitestFailed(errors)


    def guitest_test_method(self, varname):
        if varname == "data_tables":
            return guitest_check_datatables
        elif varname == "page_title":
            return guitest_check_single_value
        elif varname == "message":
            return guitest_check_element_list_with_exceeding
        else:
            return guitest_check_element_list


def guitest_check_single_value(reference, reality):
    if len(reference) > 1:
        errors.append("More than one reference value: %s" % ", ".join(reference))
    if len(reality) > 1:
        errors.append("More than one value: %s" % ", ".join(reality))
    diff_text = guitest_check_text(reference[0], reality[0])
    if diff_text:
        return [ diff_text ]
    else:
        return []


def guitest_check_element_list_with_exceeding(reference, reality):
    return guitest_check_element_list(reference, reality, check_exceeding=True)


def guitest_check_element_list(reference, reality, check_exceeding=False):
    errors = []
    one_missing = False
    for entry in reference:
        if not guitest_entry_in_reference_list(entry, reality):
            errors.append("missing entry %r" % (entry,))
            one_missing = True
    if one_missing or check_exceeding:
        for entry in reality:
            if not guitest_entry_in_reference_list(entry, reference):
                errors.append("exceeding entry %r" % (entry,))
    return errors


def guitest_entry_in_reference_list(entry, ref_list):
    for ref_entry in ref_list:
        if guitest_entries_match(ref_entry, entry):
            return True
    return False


def guitest_entries_match(ref, real):
    return guitest_drop_dynamic_ids(ref) == guitest_drop_dynamic_ids(real)



def guitest_check_datatables(reference, reality):
    if len(reference) != len(reality):
        errors = [ _("Expected %d data tables, but got %d") % (len(reference), len(reality)) ]
        if len(reference) > len(reality):
            first_table = reference[len(reality)]
            errors.append( _("First missing table has title '%s', %d rows") % (
                first_table.get("title", "(no title)"), len(first_table["rows"])))
        return errors

    errors = []
    for ref_table, real_table in zip(reference, reality):
        errors += guitest_check_datatable(ref_table, real_table)
    return errors


def guitest_check_datatable(ref_table, real_table):
    if ref_table["id"] != real_table["id"]:
        return [ "Table id %s expected, but got %s" % (ref_table["id"], real_table["id"]) ]

    if len(ref_table["rows"]) != len(real_table["rows"]):
        return [ "Table %s: expected %d rows, but got %d" % (
                  ref_table["id"], len(ref_table["rows"]), len(real_table["rows"])) ]

    for row_nr, (ref_row, real_row) in enumerate(zip(ref_table["rows"], real_table["rows"])):
        if len(ref_row) != len(real_row):
            return [ "Table %s, row %d: expected %d columns, but got %d" % (
                ref_table["id"], row_nr+1, len(ref_row), len(real_row)) ]

        # Note: Rows are tuples. The first component is the list of cells
        for cell_nr, (ref_cell, real_cell) in enumerate(zip(ref_row[0], real_row[0])):
            # Note: cell is a triple. The first component contains the text
            diff_text = guitest_check_text(ref_cell[0], real_cell[0])
            if diff_text:
                return [ "Row %d, Column %d: %s" % (row_nr, cell_nr, diff_text) ]

    return []


def guitest_check_text(ref, real):
    ref_clean = guitest_drop_dynamic_ids(ref)
    real_clean = guitest_drop_dynamic_ids(real)
    if ref_clean == real_clean:
        return ""

    prefix, ref_rest, real_rest = find_common_prefix(ref_clean, real_clean)
    return "expected %s[[[%s]]], got %s[[[%s]]]" % (prefix, ref_rest, prefix, real_rest)


def find_common_prefix(a, b):
    if len(a) > len(b) and a.startswith(b):
        return b, a[:len(b)], ""

    if len(b) > len(a) and b.startswith(a):
        return a, "", b[:len(a)]

    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return a[:i], a[i:], b[i:]

    return a, "", ""

def guitest_drop_dynamic_ids(thing):
    if type(thing) == tuple:
        return tuple(map(guitest_drop_dynamic_ids, list(thing)))
    elif type(thing) == list:
        return map(guitest_drop_dynamic_ids, thing)
    elif type(thing) in (str, unicode):
        return guitest_drop_dynamic_ids_in_text(thing)
    else:
        return thing

check_mk_version_regex = "(1\.2\.[68]?([bp][0-9]+)|1\.2\.[79]i[0-9](p[0-9]+)?|201[5-9]\.[01][0-9]\.[0123][0-9])"
timeofday_regex = "[012][0-9]:[0-5][0-9]:[0-5][0-9]"
year_regex = "201[56789]"
english_date_regex = "(Mon|Tue|Wed|Thu|Fri|Sat|Sun) +(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) +[1-9][0-9]?"


def guitest_drop_dynamic_ids_in_text(text):
    text = re.sub("selection(%3d|=)[a-f0-9---]{36}", "selection=*", text)
    text = re.sub("_transid=1[4-6][0-9]{8}/[0-9]+", "_transid=TRANSID", text)
    text = re.sub('name="_transid" value="1[0-9/]+"', 'name="_transid", value="***"', text)
    text = re.sub("<script.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(check_mk_version_regex, "CMK_VERSION", text)
    text = re.sub(timeofday_regex, "TIMEOFDAY", text)
    text = re.sub(year_regex, "YEAR", text)
    text = re.sub(english_date_regex, "DATE", text)
    return text


def pending_hosts():
    html.live.set_prepend_site(True)
    hosts = html.live.query("GET hosts\nFilter: has_been_checked = 0\nColumns: name")
    html.live.set_prepend_site(False)
    return hosts


def pending_active_services():
    html.live.set_prepend_site(True)
    services = html.live.query("GET services\nFilter: has_been_checked = 0\nFilter: check_type = 0\nColumns: host_name description")
    html.live.set_prepend_site(False)
    entries = [ (site, "%s;%s" % (host_name, service_description))
                for (site, host_name, service_description) in services ]
    return entries


def page_reschedule_all():
    if not config.guitests_enabled:
        raise MKAuthException(_("GUI Tests are disabled."))

    html.header(_("Rescheduling and waiting for check results"), stylesheets=["status", "pages"])
    wait_for_pending("host", pending_hosts, 20)
    wait_for_pending("service", pending_active_services, 100)
    html.footer()


def wait_for_pending(what, generator_function, tries):
    entries = generator_function()
    for try_number in range(tries):
        for site, entry in entries:
            html.live.command("[1231231233] SCHEDULE_FORCED_%s_CHECK;%s;%d" % (what.upper(), entry, time.time()), sitename = site)
        time.sleep(0.3)
        entries = generator_function()
        if not entries:
            html.message("All %ss are checked.\n" % what)
            break

    else:
        html.message("Reschedule failed after %d tries. Still pending %ss: %s\n" % (tries, what, ", ".join([e[1] for e in entries])))

