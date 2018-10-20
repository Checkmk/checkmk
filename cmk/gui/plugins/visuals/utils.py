#!/usr/bin/env python
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

"""Module to hold shared code for main module internals and the plugins"""

# TODO: More feature related splitting up would be better

import abc
import time

import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html

# TODO: Refactor to standard registry API
multisite_filters  = {}
# TODO: Refactor to standard registry API
_infos = {}
# TODO: Refactor to standard registry API
visual_types = {}

def declare_info(infoname, info):
    _infos[infoname] = info

def declare_filter(sort_index, f, comment = None):
    multisite_filters[f.name] = f
    f.comment = comment
    f.sort_index = sort_index

# Base class for all filters
# name:          The unique id of that filter. This id is e.g. used in the
#                persisted view configuration
# title:         The title of the filter visible to the user. This text
#                may be localized
# info:          The datasource info this filter needs to work. If this
#                is "service", the filter will also be available in tables
#                showing service information. "host" is available in all
#                service and host views. The log datasource provides both
#                "host" and "service". Look into datasource.py for which
#                datasource provides which information
# htmlvars:      HTML variables this filter uses
# link_columns:  If this filter is used for linking (state "hidden"), then
#                these Livestatus columns are needed to fill the filter with
#                the proper information. In most cases, this is just []. Only
#                a few filters are useful for linking (such as the host_name and
#                service_description filters with exact match)
class Filter(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, name, title, info, htmlvars, link_columns):
        super(Filter, self).__init__()
        self.name = name
        self.info = info
        self.title = title
        self.htmlvars = htmlvars
        self.link_columns = link_columns

    # Some filters can be unavailable due to the configuration (e.g.
    # the WATO Folder filter is only available if WATO is enabled.
    def available(self):
        return True

    # Some filters can be invisible. This is useful to hide filters which have always
    # the same value but can not be removed using available() because the value needs
    # to be set during runtime.
    # A good example is the "site" filter which does not need to be available to the
    # user in single site setups.
    def visible(self):
        return True

    # More complex filters need more height in the HTML layout
    def double_height(self):
        return False

    @abc.abstractmethod
    def display(self):
        raise NotImplementedError()

    def filter(self, infoname):
        return ""

    # Whether this filter needs to load host inventory data
    def need_inventory(self):
        return False

    # post-Livestatus filtering (e.g. for BI aggregations)
    def filter_table(self, rows):
        return rows

    def variable_settings(self, row):
        return [] # return pairs of htmlvar and name according to dataset in row

    def infoprefix(self, infoname):
        if self.info == infoname:
            return ""
        return self.info[:-1] + "_"

    # Hidden filters may contribute to the pages headers of the views
    def heading_info(self):
        return None

    # Returns the current representation of the filter settings from the HTML
    # var context. This can be used to persist the filter settings.
    def value(self):
        val = {}
        for varname in self.htmlvars:
            val[varname] = html.var(varname, '')
        return val

    # Is used to populate a value, for example loaded from persistance, into
    # the HTML context where it can be used by e.g. the display() method.
    def set_value(self, value):
        for varname in self.htmlvars:
            html.set_var(varname, value.get(varname))



# TODO: We should merge this with Filter() and make all vars unicode ...
class FilterUnicodeFilter(Filter):
    def value(self):
        val = {}
        for varname in self.htmlvars:
            val[varname] = html.get_unicode_input(varname, '')
        return val


class FilterTristate(Filter):
    def __init__(self, name, title, info, column, deflt = -1):
        self.column = column
        self.varname = "is_" + name
        super(FilterTristate, self).__init__(name, title, info, [ self.varname ], [])
        self.deflt = deflt

    def display(self):
        current = html.var(self.varname)
        html.begin_radio_group(horizontal=True)
        for value, text in [("1", _("yes")), ("0", _("no")), ("-1", _("(ignore)"))]:
            checked = current == value or (current in [ None, ""] and int(value) == self.deflt)
            html.radiobutton(self.varname, value, checked, text + " &nbsp; ")
        html.end_radio_group()

    def tristate_value(self):
        return html.get_integer_input(self.varname, self.deflt)

    def filter(self, infoname):
        current = self.tristate_value()
        if current == -1: # ignore
            return ""
        elif current == 1:
            return self.filter_code(infoname, True)
        return self.filter_code(infoname, False)

    def filter_code(self, infoname, positive):
        raise NotImplementedError()


class FilterTime(Filter):
    """Filter for setting time ranges, e.g. on last_state_change and last_check"""
    def __init__(self, info, name, title, column):
        self.column = column
        self.name = name
        self.ranges = [
           (86400,  _("days")),
           (3600,   _("hours")),
           (60,     _("min")),
           (1,      _("sec")),
        ]
        varnames = [ name + "_from", name + "_from_range",
                     name + "_until", name + "_until_range" ]

        super(FilterTime, self).__init__(name, title, info, varnames, [column])


    def double_height(self):
        return True

    def display(self):
        choices = [ (str(sec), title + " " + _("ago")) for sec, title in self.ranges ] + \
                  [ ("abs", _("Date (YYYY-MM-DD)")),
                    ("unix", _("UNIX timestamp")) ]

        html.open_table(class_="filtertime")
        for what, whatname in [
            ( "from", _("From") ),
            ( "until", _("Until") ) ]:
            varprefix = self.name + "_" + what
            html.open_tr()
            html.open_td()
            html.write("%s:" % whatname)
            html.close_td()
            html.open_td()
            html.text_input(varprefix, style="width: 116px;")
            html.close_td()
            html.open_td()
            html.dropdown(varprefix + "_range", choices, deflt="3600")
            html.close_td()
            html.close_tr()
        html.close_table()


    def filter(self, infoname):
        fromsecs, untilsecs = self.get_time_range()
        filtertext = ""
        if fromsecs != None:
            filtertext += "Filter: %s >= %d\n" % (self.column, fromsecs)
        if untilsecs != None:
            filtertext += "Filter: %s <= %d\n" % (self.column, untilsecs)
        return filtertext


    # Extract timerange user has selected from HTML variables
    def get_time_range(self):
        return self._get_time_range_of("from"), \
               self._get_time_range_of("until")


    def _get_time_range_of(self, what):
        varprefix = self.name + "_" + what

        rangename = html.var(varprefix + "_range")
        if rangename == "abs":
            try:
                return time.mktime(time.strptime(html.var(varprefix), "%Y-%m-%d"))
            except:
                html.add_user_error(varprefix, _("Please enter the date in the format YYYY-MM-DD."))
                return None

        elif rangename == "unix":
            return html.get_integer_input(varprefix)

        try:
            count = html.get_integer_input(varprefix)
            secs = count * int(rangename)
            return int(time.time()) - secs
        except:
            html.set_var(varprefix, "")
            return None


class FilterSite(Filter):
    def __init__(self, name, enforce):
        super(FilterSite, self).__init__(name, _("Site") + (enforce and _( " (enforced)") or ""), 'host', ["site"], [])
        self.enforce = enforce


    def display(self):
        html.dropdown("site", self._choices())


    def _choices(self):
        if self.enforce:
            choices = []
        else:
            choices = [("","")]

        for sitename, state in sites.states().items():
            if state["state"] == "online":
                choices.append((sitename, config.site(sitename)["alias"]))

        return sorted(choices, key=lambda a: a[1].lower())


    def heading_info(self):
        current_value = html.var("site")
        if current_value:
            alias = config.site(current_value)["alias"]
            return alias


    def variable_settings(self, row):
        return [("site", row["site"])]
