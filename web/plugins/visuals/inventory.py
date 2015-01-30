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

import inventory

# Try to magically compare two software versions.
# Currently we only assume the format A.B.C.D....
# When we suceed converting A to a number, then we
# compare by integer, otherwise by text.
def try_int(x):
    try:
        return int(x)
    except:
        return x

def cmp_version(a, b):
    if a == None or b == None:
        return cmp(a, b)
    aa = map(try_int, a.split("."))
    bb = map(try_int, b.split("."))
    return cmp(aa, bb)

class FilterInvText(Filter):
    def __init__(self, name, invpath, title):
        self._invpath = invpath
        Filter.__init__(self, name, title, "host", [name], [])

    def need_inventory(self):
        return True

    def display(self):
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar, "")
        html.text_input(htmlvar, current_value)

    def filter_table(self, rows):
        htmlvar = self.htmlvars[0]
        filtertext = html.var(htmlvar, "").strip().lower()
        if not filtertext:
            return rows

        regex = re.compile(filtertext, re.IGNORECASE)

        newrows = []
        for row in rows:
            invdata = inventory.get(row["host_inventory"], self._invpath)
            if invdata == None:
                invdata = ""
            if regex.search(invdata):
                newrows.append(row)
        return newrows

class FilterInvFloat(Filter):
    def __init__(self, name, invpath, title, unit="", scale=1.0):
        self._invpath = invpath
        self._unit = unit
        self._scale = scale
        Filter.__init__(self, name, title, "host", [name + "_from", name + "_to"], [])

    def need_inventory(self):
        return True

    def display(self):
        html.write(_("From: "))
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar, "")
        html.number_input(htmlvar, current_value)
        if self._unit:
            html.write(self._unit)

        html.write("&nbsp;&nbsp;" + _("To: " ))
        htmlvar = self.htmlvars[1]
        current_value = html.var(htmlvar, "")
        html.number_input(htmlvar, current_value)
        if self._unit:
            html.write(self._unit)

    def filter_table(self, rows):
        fromvar = self.htmlvars[0]
        fromtext = html.var(fromvar)
        lower = None
        if fromtext:
            try:
                lower = float(fromtext) * self._scale
            except:
                pass

        tovar = self.htmlvars[1]
        totext = html.var(tovar)
        upper = None
        if totext:
            try:
                upper = float(totext) * self._scale
            except:
                pass

        if lower == None and upper == None:
            return rows

        newrows = []
        for row in rows:
            invdata = inventory.get(row["host_inventory"], self._invpath)
            if lower != None and invdata < lower:
                continue
            if upper != None and invdata > upper:
                continue
            newrows.append(row)
        return newrows

class FilterHasInventory(FilterTristate):
    def __init__(self):
        FilterTristate.__init__(self, "has_inv", _("Has Inventory Data"), "host", "host_inventory")

    def filter(self, infoname):
        return "" # No Livestatus filtering right now

    def filter_table(self, rows):
        tri = self.tristate_value()
        if tri == -1:
            return rows
        elif tri == 1:
            return [ row for row in rows if row["host_inventory"] ]
        else: # not
            return [ row for row in rows if not row["host_inventory"] ]

declare_filter(801, FilterHasInventory())

class FilterInvHasSoftwarePackage(Filter):
    def __init__(self):
        self._varprefix = "invswpac_host_"
        Filter.__init__(self, "invswpac", _("Host has software package"), "host",
                        [ self._varprefix + "name", self._varprefix + "version_from",
                          self._varprefix + "version_to", self._varprefix + "negate"], [])

    def double_height(self):
        return True

    def need_inventory(self):
        return True

    def display(self):
        html.text_input(self._varprefix + "name")
        html.write("<br>")
        html.begin_radio_group(horizontal=True)
        html.radiobutton(self._varprefix + "match", "exact", True, label=_("exact match"))
        html.radiobutton(self._varprefix + "match", "regex", False, label=_("regular expression, substring match"))
        html.end_radio_group()
        html.write("<br>")
        html.write(_("Min.&nbsp;Version:"))
        html.text_input(self._varprefix + "version_from", size = 9)
        html.write(" &nbsp; ")
        html.write(_("Max.&nbsp;Vers.:"))
        html.text_input(self._varprefix + "version_to", size = 9)
        html.write("<br>")
        html.checkbox(self._varprefix + "negate", False, label=_("Negate: find hosts <b>not</b> having this package"))

    def filter_table(self, rows):
        name = html.var_utf8(self._varprefix + "name")
        if not name:
            return rows

        from_version = html.var(self._varprefix + "from_version")
        to_version   = html.var(self._varprefix + "to_version")
        negate       = html.get_checkbox(self._varprefix + "negate")
        match        = html.var(self._varprefix + "match")
        if match == "regex":
            name = re.compile(name)

        new_rows = []
        for row in rows:
            packages = inventory.get(row["host_inventory"], ".software.packages:")
            is_in = self.find_package(packages, name, from_version, to_version)
            if is_in != negate:
                new_rows.append(row)
        return new_rows

    def find_package(self, packages, name, from_version, to_version):
        for package in packages:
            if type(name) == unicode:
                if package["name"] != name:
                    continue
            else:
                if not name.search(package["name"]):
                    continue
            if not from_version and not to_version:
                return True # version not relevant
            version = package["version"]
            if from_version == to_version and from_version != version:
                continue
            if from_version and self.version_is_lower(version, from_version):
                continue
            if to_version and self.version_is_higher(version, to_version):
                continue
        return False

    def version_is_lower(self, a, b):
        return a != b and not self.version_is_higher(a, b)

    def version_is_higher(self, a, b):
        return cmp_version(a, b) == 1

declare_filter(801, FilterInvHasSoftwarePackage())

class FilterSWPacsText(Filter):
    def __init__(self, name, title):
        varname = "invswpac_" + name
        Filter.__init__(self, varname, title, "invswpacs", [varname], [])

    def display(self):
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar, "")
        html.text_input(htmlvar, current_value)

    def filter_table(self, rows):
        htmlvar = self.htmlvars[0]
        filtertext = html.var(htmlvar, "").strip().lower()
        if not filtertext:
            return rows

        regex = re.compile(filtertext, re.IGNORECASE)

        newrows = []
        for row in rows:
            if regex.search(row.get(htmlvar, "")):
                newrows.append(row)
        return newrows

class FilterSWPacsVersion(Filter):
    def __init__(self, name, title):
        varname = "invswpac_" + name
        Filter.__init__(self, varname, title, "invswpacs", [varname + "_from", varname + "_to"], [])

    def display(self):
        htmlvar = self.htmlvars[0]
        html.write(_("Min.&nbsp;Version:"))
        html.text_input(self.htmlvars[0], size = 9)
        html.write(" &nbsp; ")
        html.write(_("Max.&nbsp;Version:"))
        html.text_input(self.htmlvars[1], size = 9)

    def filter_table(self, rows):
        from_version = html.var(self.htmlvars[0])
        to_version   = html.var(self.htmlvars[1])
        if not from_version and not to_version:
            return rows # Filter not used

        new_rows = []
        for row in rows:
            version = row.get(self.name, "")
            if from_version and cmp_version(version, from_version) == -1:
                continue
            if to_version and cmp_version(version, to_version) == 1:
                continue
            new_rows.append(row)

        return new_rows

