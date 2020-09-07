#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for main module internals and the plugins"""

# TODO: More feature related splitting up would be better

import abc
import time
from typing import Dict, List, Optional, Tuple, Union, Type, Iterator

from cmk.gui.exceptions import MKGeneralException
from cmk.gui.valuespec import ValueSpec

import cmk.utils.plugin_registry

import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.view_utils import get_labels
from cmk.gui.type_defs import ColumnName, HTTPVariables
from cmk.gui.htmllib import Choices
from cmk.gui.page_menu import PageMenuEntry


class VisualInfo(metaclass=abc.ABCMeta):
    """Base class for all visual info classes"""
    @abc.abstractproperty
    def ident(self) -> str:
        """The identity of a visual type. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        """The human readable GUI title"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title_plural(self) -> str:
        """The human readable GUI title for multiple items"""
        raise NotImplementedError()

    @abc.abstractproperty
    def single_spec(self) -> List[Tuple[str, ValueSpec]]:
        """The key / valuespec pairs (choices) to identify a single row"""
        raise NotImplementedError()

    @property
    def multiple_site_filters(self) -> List[str]:
        """Returns a list of filter identifiers.

        When these filters are set, the site hint will not be added to urls
        which link to views using this datasource, because the resuling view
        should show the objects spread accross the sites"""
        return []

    @property
    def single_site(self) -> bool:
        """When there is one non single site info used by a visual
        don't add the site hint"""
        return True

    @property
    def sort_index(self) -> int:
        """Used for sorting when listing multiple infos. Lower is displayed first"""
        return 30


class VisualInfoRegistry(cmk.utils.plugin_registry.Registry[Type[VisualInfo]]):
    def plugin_name(self, instance):
        return instance().ident

    # At least painter <> info matching extracts the info name from the name of the painter by
    # splitting at first "_" and use the text before it as info name. See
    # cmk.gui.views.infos_needed_by_painter().
    def registration_hook(self, instance):
        ident = instance().ident
        if ident == "aggr_group":
            return  # TODO: Allow this broken thing for the moment
        if "_" in ident:
            raise MKGeneralException("Underscores must not be used in info names: %s" % ident)


visual_info_registry = VisualInfoRegistry()


class VisualType(metaclass=abc.ABCMeta):
    """Base class for all filters"""
    @abc.abstractproperty
    def ident(self) -> str:
        """The identity of a visual type. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        """The human readable GUI title"""
        raise NotImplementedError()

    @abc.abstractproperty
    def ident_attr(self) -> str:
        """The name of the attribute that is used to identify a visual of this type"""
        raise NotImplementedError()

    @abc.abstractproperty
    def multicontext_links(self) -> bool:
        """Whether or not to show context buttons even if not single infos present"""
        raise NotImplementedError()

    @abc.abstractproperty
    def plural_title(self) -> str:
        """The plural title to use in the GUI"""
        raise NotImplementedError()

    @abc.abstractproperty
    def show_url(self) -> str:
        """The URL filename that can be used to show visuals of this type"""
        raise NotImplementedError()

    @abc.abstractmethod
    def add_visual_handler(self, target_visual_name: str, add_type: str, context: Dict,
                           parameters: Dict) -> None:
        """The function to handle adding the given visual to the given visual of this type"""
        raise NotImplementedError()

    @abc.abstractmethod
    def page_menu_add_to_entries(self, add_type: str) -> Iterator[PageMenuEntry]:
        """List of visual choices another visual of the given type can be added to"""
        raise NotImplementedError()

    @abc.abstractmethod
    def load_handler(self) -> None:
        """Load all visuals of this type"""
        raise NotImplementedError()

    @abc.abstractproperty
    def permitted_visuals(self) -> Dict:
        """Get the permitted visuals of this type"""
        raise NotImplementedError()

    def link_from(self, linking_view, linking_view_rows, visual, context_vars):
        """Dynamically show/hide links to other visuals (e.g. reports, dashboards, views) from views

        This method uses the conditions read from the "link_from" attribute of a given visual to
        decide whether or not the given linking_view should show a link to the given visual.

        The decision can be made based on the given context_vars, linking_view definition and
        linking_view_rows. Currently there is only a small set of conditions implemented here.

        single_infos: Only link when the given list of single_infos match.
        host_labels: Only link when the given host labels match.

        Example: The visual with this definition will only be linked from host detail pages of hosts
        that are Checkmk servers.

        'link_from': {
            'single_infos': ["host"],
            'host_labels': {
                'cmk/check_mk_server': 'yes'
            }
        }
        """
        link_from = visual["link_from"]
        if not link_from:
            return True  # No link from filtering: Always display this.

        single_info_condition = link_from.get("single_infos")
        if single_info_condition and not set(single_info_condition).issubset(
                linking_view.spec["single_infos"]):
            return False  # Not matching required single infos

        # Currently implemented very specific for the cases we need at the moment. Build something
        # more generic once we need it.
        if single_info_condition != ["host"]:
            raise NotImplementedError()

        if not linking_view_rows:
            return False  # Unknown host, no linking

        # In case we have rows of a single host context we only have a single row that holds the
        # host information. In case we have multiple rows, we normally have service rows which
        # all hold the same host information in their host columns.
        row = linking_view_rows[0]

        # Exclude by host labels
        host_labels = get_labels(row, "host")
        for label_group_id, label_value in link_from.get("host_labels", {}).items():
            if host_labels.get(label_group_id) != label_value:
                return False

        return True


class VisualTypeRegistry(cmk.utils.plugin_registry.Registry[Type[VisualType]]):
    def plugin_name(self, instance):
        return instance().ident


visual_type_registry = VisualTypeRegistry()


class Filter(metaclass=abc.ABCMeta):
    """Base class for all filters"""
    def __init__(self,
                 *,
                 ident: str,
                 title: str,
                 sort_index: int,
                 info: str,
                 htmlvars: List[str],
                 link_columns: List[ColumnName],
                 description: Optional[str] = None) -> None:
        """
        info:          The datasource info this filter needs to work. If this
                       is "service", the filter will also be available in tables
                       showing service information. "host" is available in all
                       service and host views. The log datasource provides both
                       "host" and "service". Look into datasource.py for which
                       datasource provides which information
        htmlvars:      HTML variables this filter uses
        link_columns:  If this filter is used for linking (state "hidden"), then
                       these Livestatus columns are needed to fill the filter with
                       the proper information. In most cases, this is just []. Only
                       a few filters are useful for linking (such as the host_name and
                       service_description filters with exact match)
        """
        self.ident = ident
        self.title = title
        self.sort_index = sort_index
        self.info = info
        self.htmlvars = htmlvars
        self.link_columns = link_columns
        self.description = description

    @property
    def is_advanced(self) -> bool:
        """Whether or not treat this as advanced GUI element"""
        return False

    def available(self) -> bool:
        """Some filters can be unavailable due to the configuration
        (e.g. the WATO Folder filter is only available if WATO is enabled."""
        return True

    def visible(self) -> bool:
        """Some filters can be invisible. This is useful to hide filters which have always
        the same value but can not be removed using available() because the value needs
        to be set during runtime.
        A good example is the "site" filter which does not need to be available to the
        user in single site setups."""
        return True

    @abc.abstractmethod
    def display(self) -> None:
        raise NotImplementedError()

    def filter(self, infoname: str) -> str:
        return ""

    def need_inventory(self) -> bool:
        """Whether this filter needs to load host inventory data"""
        return False

    def validate_value(self, value: Dict) -> None:
        return

    def filter_table(self, rows: List[dict]) -> List[dict]:
        """post-Livestatus filtering (e.g. for BI aggregations)"""
        return rows

    def variable_settings(self, row: dict) -> HTTPVariables:
        """return pairs of htmlvar and name according to dataset in row"""
        return []

    def infoprefix(self, infoname: str) -> str:
        if self.info == infoname:
            return ""
        return self.info[:-1] + "_"

    def heading_info(self) -> Optional[str]:
        """Hidden filters may contribute to the pages headers of the views"""
        return None

    def value(self):
        """Returns the current representation of the filter settings from the HTML
        var context. This can be used to persist the filter settings."""
        val = {}
        for varname in self.htmlvars:
            val[varname] = html.request.var(varname, '')
        return val

    def set_value(self, value):
        """Is used to populate a value, for example loaded from persistance, into
        the HTML context where it can be used by e.g. the display() method."""
        for varname in self.htmlvars:
            var_value = value.get(varname)
            if var_value is not None:
                html.request.set_var(varname, var_value)


class FilterTristate(Filter):
    def __init__(self,
                 *,
                 ident: str,
                 title: str,
                 sort_index: int,
                 info: str,
                 column: Optional[str],
                 deflt: int = -1):
        self.column = column
        self.varname = "is_" + ident
        super().__init__(ident=ident,
                         title=title,
                         sort_index=sort_index,
                         info=info,
                         htmlvars=[self.varname],
                         link_columns=[])
        self.deflt = deflt

    def display(self):
        current = html.request.var(self.varname)
        html.begin_radio_group(horizontal=True)
        for value, text in [("1", _("yes")), ("0", _("no")), ("-1", _("(ignore)"))]:
            checked = current == value or (current in [None, ""] and int(value) == self.deflt)
            html.radiobutton(self.varname, value, checked, text + u" &nbsp; ")
        html.end_radio_group()

    def tristate_value(self):
        return html.request.get_integer_input_mandatory(self.varname, self.deflt)

    def filter(self, infoname):
        current = self.tristate_value()
        if current == -1:  # ignore
            return ""
        if current == 1:
            return self.filter_code(infoname, True)
        return self.filter_code(infoname, False)

    def filter_code(self, infoname, positive):
        raise NotImplementedError()


class FilterTime(Filter):
    """Filter for setting time ranges, e.g. on last_state_change and last_check"""
    def __init__(self, *, ident: str, title: str, sort_index: int, info: str,
                 column: Optional[str]):
        self.column = column
        self.ranges = [
            (86400, _("days")),
            (3600, _("hours")),
            (60, _("min")),
            (1, _("sec")),
        ]
        varnames = [
            ident + "_from",
            ident + "_from_range",
            ident + "_until",
            ident + "_until_range",
        ]

        super().__init__(ident=ident,
                         title=title,
                         sort_index=sort_index,
                         info=info,
                         htmlvars=varnames,
                         link_columns=[column] if column is not None else [])

    def display(self):
        choices: Choices = [(str(sec), title + " " + _("ago")) for sec, title in self.ranges]
        choices += [("abs", _("Date (YYYY-MM-DD)")), ("unix", _("UNIX timestamp"))]

        html.open_table(class_="filtertime")
        for what, whatname in [("from", _("From")), ("until", _("Until"))]:
            varprefix = self.ident + "_" + what
            html.open_tr()
            html.open_td()
            html.write("%s:" % whatname)
            html.close_td()
            html.open_td()
            html.text_input(varprefix)
            html.close_td()
            html.open_td()
            html.dropdown(varprefix + "_range", choices, deflt="3600")
            html.close_td()
            html.close_tr()
        html.close_table()

    def filter(self, infoname):
        fromsecs, untilsecs = self.get_time_range()
        filtertext = ""
        if fromsecs is not None:
            filtertext += "Filter: %s >= %d\n" % (self.column, fromsecs)
        if untilsecs is not None:
            filtertext += "Filter: %s <= %d\n" % (self.column, untilsecs)
        return filtertext

    # Extract timerange user has selected from HTML variables
    def get_time_range(self):
        return self._get_time_range_of("from"), \
               self._get_time_range_of("until")

    def _get_time_range_of(self, what: str) -> Union[None, int, float]:
        varprefix = self.ident + "_" + what

        rangename = html.request.var(varprefix + "_range")
        if rangename == "abs":
            try:
                return time.mktime(
                    time.strptime(html.request.get_str_input_mandatory(varprefix), "%Y-%m-%d"))
            except Exception:
                html.add_user_error(varprefix, _("Please enter the date in the format YYYY-MM-DD."))
                return None

        if rangename == "unix":
            return html.request.get_integer_input_mandatory(varprefix)
        if rangename is None:
            return None

        try:
            count = html.request.get_integer_input_mandatory(varprefix)
            secs = count * int(rangename)
            return int(time.time()) - secs
        except Exception:
            html.request.set_var(varprefix, "")
            return None


def filter_cre_choices():
    return sorted([(sitename, config.site(sitename)["alias"])
                   for sitename, state in sites.states().items()
                   if state["state"] == "online"],
                  key=lambda a: a[1].lower())


def filter_cre_heading_info():
    current_value = html.request.var("site")
    return config.site(current_value)["alias"] if current_value else None


class FilterRegistry(cmk.utils.plugin_registry.Registry[Filter]):
    def plugin_name(self, instance):
        return instance.ident


filter_registry = FilterRegistry()
