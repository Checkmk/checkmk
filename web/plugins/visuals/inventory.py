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

import inventory
import cmk.defines as defines

# Try to magically compare two software versions.
# Currently we only assume the format A.B.C.D....
# When we suceed converting A to a number, then we
# compare by integer, otherwise by text.
def try_int(x):
    try:
        return int(x)
    except:
        return x


class FilterInvtableText(Filter):
    def __init__(self, infoname, name, title):
        varname = infoname + "_" + name
        Filter.__init__(self, varname, title, infoname, [varname], [])

    def display(self):
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar, "")
        html.text_input(htmlvar, current_value)

    def filter_table(self, rows):
        htmlvar = self.htmlvars[0]
        filtertext = html.var(htmlvar, "").strip().lower()
        if not filtertext:
            return rows

        try:
            regex = re.compile(filtertext, re.IGNORECASE)
        except re.error:
            raise MKUserError(htmlvar,
              _('You search statement is not valid. You need to provide a regular '
                'expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> '
                'if you like to search for a single backslash.'))

        newrows = []
        for row in rows:
            if regex.search(row.get(htmlvar, "")):
                newrows.append(row)
        return newrows



# Filter for choosing a range in which an age lies
class FilterInvtableAge(Filter):
    def __init__(self, infoname, name, title, only_days=False):
        name = infoname + "_" + name
        Filter.__init__(self, name, title, infoname, [name + "_from", name + "_to"], [])

    def display(self):
        html.open_table()

        html.open_tr()
        html.td("%s:" % _("from"), style="vertical-align: middle;")
        html.open_td()
        Age(display=["days"]).render_input(self.name + "_from", 0)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.td("%s:" % _("to"), style="vertical-align: middle;")
        html.open_td()
        Age(display=["days"]).render_input(self.name + "_to", 0)
        html.close_td()
        html.close_tr()

        html.close_table()


    def double_height(self):
        return True


    def filter_table(self, rows):
        return self.filter_table_with_conversion(rows, lambda age: age)


    def filter_table_with_conversion(self, rows, conv):
        from_value = Age().from_html_vars(self.name + "_from")
        to_value = Age().from_html_vars(self.name + "_to")

        if not from_value and not to_value:
            return rows

        newrows = []
        for row in rows:
            value = row.get(self.name, None)
            if value != None:
                age = conv(value)
                if from_value and age < from_value:
                    continue

                if to_value and age > to_value:
                    continue
                newrows.append(row)
        return newrows



class FilterInvtableTimestampAsAge(FilterInvtableAge):
    def __init__(self, infoname, name, title, only_days=True):
        FilterInvtableAge.__init__(self, infoname, name, title, only_days)


    def filter_table(self, rows):
        now = time.time()
        return self.filter_table_with_conversion(rows, lambda timestamp: now - timestamp)



# Filter for choosing a range in which a certain integer lies
class FilterInvtableIDRange(Filter):
    def __init__(self, infoname, name, title):
        name = infoname + "_" + name
        Filter.__init__(self, name, title, infoname, [name + "_from", name + "_to"], [])

    def display(self):
        html.write_text(_("from:") + " ")
        html.number_input(self.name + "_from")
        html.write_text("&nbsp; %s: " % _("to"))
        html.number_input(self.name + "_to")

    def filter_table(self, rows):
        from_value = saveint(html.var(self.name + "_from"))
        to_value = saveint(html.var(self.name + "_to"))

        if not from_value and not to_value:
            return rows

        newrows = []
        for row in rows:
            value = row.get(self.name, None)
            if value != None:
                if from_value and value < from_value:
                    continue

                if to_value and value > to_value:
                    continue
                newrows.append(row)
        return newrows


class FilterInvtableOperStatus(Filter):
    def __init__(self, infoname, name, title):
        varname = infoname + "_" + name
        varnames = [ varname + "_" + str(x) for x in defines.interface_oper_states() ]
        Filter.__init__(self, varname, title, infoname, varnames, [])

    def display(self):
        html.begin_checkbox_group()
        for state, state_name in sorted(defines.interface_oper_states().items()):
            if state >= 8:
                continue # skip artificial state 8 (degraded) and 9 (admin down)
            varname = self.name + "_" + str(state)
            html.checkbox(varname, True, label=state_name)
            if state in (4, 7):
                html.br()
        html.end_checkbox_group()

    def double_height(self):
        return True

    def filter_table(self, rows):
        # We consider the filter active if not all checkboxes
        # are either on (default) or off (unset)
        settings = set([])
        for varname in self.htmlvars:
            settings.add(html.var(varname))
        if len(settings) == 1:
            return rows

        new_rows = []
        for row in rows:
            oper_status = row["invinterface_oper_status"]
            varname = "%s_%d" % (self.name, oper_status)
            if html.get_checkbox(varname):
                new_rows.append(row)
        return new_rows


class FilterInvtableAdminStatus(Filter):
    def __init__(self, infoname, name, title):
        varname = infoname + "_" + name
        Filter.__init__(self, varname, title, infoname, [ varname ], [])

    def display(self):
        html.begin_radio_group(horizontal=True)
        for value, text in [("1", _("up")), ("2", _("down")), ("-1", _("(ignore)"))]:
            html.radiobutton(self.name, value, value == "-1", text + " &nbsp; ")
        html.end_radio_group()

    def filter_table(self, rows):
        current = html.var(self.name)
        if current not in ("1", "2"):
            return rows

        new_rows = []
        for row in rows:
            admin_status = str(row["invinterface_admin_status"])
            if admin_status == current:
                new_rows.append(row)
        return new_rows

class FilterInvtableAvailable(Filter):
    def __init__(self, infoname, name, title):
        varname = infoname + "_" + name
        Filter.__init__(self, varname, title, infoname, [ varname ], [])

    def display(self):
        html.begin_radio_group(horizontal=True)
        for value, text in [("no", _("used")), ("yes", _("free")), ("", _("(ignore)"))]:
            html.radiobutton(self.name, value, value == "", text + " &nbsp; ")
        html.end_radio_group()

    def filter_table(self, rows):
        current = html.var(self.name)
        if current not in ("no", "yes"):
            return rows

        f = current == "yes"

        new_rows = []
        for row in rows:
            available = row.get("invinterface_available")
            if available == f:
                new_rows.append(row)
        return new_rows


class FilterInvtableInterfaceType(Filter):
    def __init__(self, infoname, name, title):
        varname = infoname + "_" + name
        Filter.__init__(self, varname, title, infoname, [ varname ], [])

    def double_height(self):
        return True

    def valuespec(self):
        return DualListChoice(
            choices = interface_port_type_choices,
            rows = 4,
            enlarge_active = True,
            custom_order = True)

    def selection(self):
        current = html.var(self.name, "").strip().split("|")
        if current == ['']:
            return []
        else:
            return current

    def display(self):
        html.open_div(class_="multigroup")
        self.valuespec().render_input(self.name, self.selection())
        html.close_div()

    def filter_table(self, rows):
        current = self.selection()
        if len(current) == 0:
            return rows # No types selected, filter is unused
        new_rows = []
        for row in rows:
            if str(row[self.name]) in current:
                new_rows.append(row)
        return new_rows


class FilterInvtableVersion(Filter):
    def __init__(self, infoname, name, title):
        varname = infoname + "_" + name
        Filter.__init__(self, varname, title, infoname, [varname + "_from", varname + "_to"], [])

    def display(self):
        htmlvar = self.htmlvars[0]
        html.write_text(_("Min.&nbsp;Version:"))
        html.text_input(self.htmlvars[0], size=9)
        html.write_text(" &nbsp; ")
        html.write_text(_("Max.&nbsp;Version:"))
        html.text_input(self.htmlvars[1], size=9)

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

        try:
            regex = re.compile(filtertext, re.IGNORECASE)
        except re.error:
            raise MKUserError(htmlvar,
              _('You search statement is not valid. You need to provide a regular '
                'expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> '
                'if you like to search for a single backslash.'))

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
        html.write_text(_("From: "))
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar, "")
        html.number_input(htmlvar, current_value)
        if self._unit:
            html.write(self._unit)

        html.write_text("&nbsp;&nbsp;" + _("To: " ))
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


class FilterInvBool(FilterTristate):
    def __init__(self, name, invpath, title):
        self._invpath = invpath
        FilterTristate.__init__(self, name, title, "host", name)

    def need_inventory(self):
        return True

    def filter(self, infoname):
        return "" # No Livestatus filtering right now

    def filter_table(self, rows):
        tri = self.tristate_value()
        if tri == -1:
            return rows
        else:
            wanted_value = tri == 1

            newrows = []
            for row in rows:
                invdata = inventory.get(row["host_inventory"], self._invpath)
                if wanted_value == invdata:
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
        html.br()
        html.begin_radio_group(horizontal=True)
        html.radiobutton(self._varprefix + "match", "exact", True, label=_("exact match"))
        html.radiobutton(self._varprefix + "match", "regex", False, label=_("regular expression, substring match"))
        html.end_radio_group()
        html.br()
        html.write_text(_("Min.&nbsp;Version:"))
        html.text_input(self._varprefix + "version_from", size=9)
        html.write_text(" &nbsp; ")
        html.write_text(_("Max.&nbsp;Vers.:"))
        html.text_input(self._varprefix + "version_to", size=9)
        html.br()
        html.checkbox(self._varprefix + "negate", False, label=_("Negate: find hosts <b>not</b> having this package"))

    def filter_table(self, rows):
        name = html.get_unicode_input(self._varprefix + "name")
        if not name:
            return rows

        from_version = html.var(self._varprefix + "from_version")
        to_version   = html.var(self._varprefix + "to_version")
        negate       = html.get_checkbox(self._varprefix + "negate")
        match        = html.var(self._varprefix + "match")
        if match == "regex":
            try:
                name = re.compile(name)
            except re.error:
                raise MKUserError(self._varprefix + "name",
                  _('You search statement is not valid. You need to provide a regular '
                    'expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> '
                    'if you like to search for a single backslash.'))

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


