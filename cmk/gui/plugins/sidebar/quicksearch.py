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

import abc
import re
import traceback
import six

import livestatus

import cmk.utils.plugin_registry

import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import HTTPRedirect, MKGeneralException, MKException
from cmk.gui.plugins.sidebar import SidebarSnapin, snapin_registry


@snapin_registry.register
class QuicksearchSnapin(SidebarSnapin):
    @staticmethod
    def type_name():
        return "search"

    @classmethod
    def title(cls):
        return _("Quicksearch")

    @classmethod
    def description(cls):
        return _("Interactive search field for direct access to hosts, services, host- and "\
                 "servicegroups.<br>You can use the following filters:<br> <i>h:</i> Host, <i>s:</i> Service<br> "\
                 "<i>hg:</i> Hostgroup, <i>sg:</i> Servicegroup<br><i>ad:</i> Address, <i>al:</i> Alias, <i>tg:</i> Hosttag")

    def show(self):
        html.open_div(id_="mk_side_search",
                      class_="content_center",
                      onclick="cmk.quicksearch.close_popup();")
        html.input(id_="mk_side_search_field", type_="text", name="search", autocomplete="off")
        html.icon_button("#",
                         _("Search"),
                         "quicksearch",
                         onclick="cmk.quicksearch.on_search_click();")
        html.close_div()
        html.div('', id_="mk_side_clear")
        html.javascript("cmk.quicksearch.register_search_field('mk_side_search_field');")

    @classmethod
    def allowed_roles(cls):
        return ["user", "admin", "guest"]

    def page_handlers(self):
        return {
            "ajax_search": self._ajax_search,
            "search_open": self._page_search_open,
        }

    def _ajax_search(self):
        q = html.get_unicode_input('q').strip()
        if not q:
            return

        try:
            generate_results(q)
        except MKException as e:
            html.show_error(e)
        except Exception as e:
            logger.exception("error generating quicksearch results")
            if config.debug:
                raise
            html.show_error(traceback.format_exc())

    def _page_search_open(self):
        q = html.request.var('q').strip()
        if not q:
            return

        url = generate_search_results(q)
        raise HTTPRedirect(url)


# Ensures the provided search string is a regex, does some basic conversion
# and then tries to verify it is a regex
def _to_regex(s):
    s = s.replace('*', '.*')
    try:
        re.compile(s)
    except re.error:
        raise MKGeneralException(
            _('You search statement is not valid. You need to provide a regular '
              'expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> '
              'if you like to search for a single backslash.'))
    return s


class TooManyRowsError(MKException):
    pass


class LivestatusSearchBase(object):
    def _build_url(self, url_params, restore_regex=False):
        new_params = []
        if restore_regex:
            for key, value in url_params:
                new_params.append((key, value.replace("\\", "\\\\")))
        else:
            new_params.extend(url_params)
        return html.makeuri(new_params, delvars="q", filename="view.py")


# Handles exactly one livestatus query
class LivestatusSearchConductor(LivestatusSearchBase):
    def __init__(self, used_filters, filter_behaviour):
        # used_filters:     {u'h': [u'heute'], u's': [u'Check_MK']}
        # filter_behaviour: "continue"
        self._used_filters = used_filters
        self._filter_behaviour = filter_behaviour

        self._livestatus_command = None  # Computed livestatus query
        self._rows = []  # Raw data from livestatus
        self._elements = []  # Postprocessed rows

    def get_filter_behaviour(self):
        return self._filter_behaviour

    def do_query(self):
        self._execute_livestatus_command()

    def num_rows(self):
        return len(self._rows)

    def remove_rows_from_end(self, num):
        self._rows = self._rows[:-num]

    def row_limit_exceeded(self):
        return self._too_much_rows

    def get_elements(self):
        return self._elements

    def get_match_topic(self):
        if len(self._used_filters.keys()) > 1:
            return "Multi-Filter"
        shortname = self._used_filters.keys()[0]
        return self._get_plugin_with_shortname(shortname).get_match_topic()

    def _get_plugin_with_shortname(self, shortname):
        for plugin_class in match_plugin_registry.values():
            plugin = plugin_class()
            if plugin.get_filter_shortname() == shortname:
                return plugin
        raise NotImplementedError()

    def _execute_livestatus_command(self):
        self._rows = []
        self._too_much_rows = False

        self._generate_livestatus_command()

        if not self._livestatus_command:
            return

        sites.live().set_prepend_site(True)
        results = sites.live().query(self._livestatus_command)
        sites.live().set_prepend_site(False)

        # Invalid livestatus response, missing headers..
        if not results:
            return

        headers = ["site"] + self._queried_livestatus_columns
        self._rows = [dict(zip(headers, x)) for x in results]

        limit = config.quicksearch_dropdown_limit
        if len(self._rows) > limit:
            self._too_much_rows = True
            self._rows.pop()  # Remove limit+1nth element

    def _generate_livestatus_command(self):
        self._determine_livestatus_table()
        columns_to_query = set(self._get_livestatus_default_columns())
        livestatus_filter_domains = {}  # Filters sorted by domain

        self._used_search_plugins = self._get_used_search_plugins()

        for plugin in self._used_search_plugins:
            columns_to_query.update(set(plugin.get_livestatus_columns(self._livestatus_table)))
            name = plugin.get_filter_shortname()
            livestatus_filter_domains.setdefault(name, [])
            livestatus_filter_domains[name].append(
                plugin.get_livestatus_filters(self._livestatus_table, self._used_filters))

        # Combine filters of same domain (h/s/sg/hg/..)
        livestatus_filters = []
        for entries in livestatus_filter_domains.values():
            livestatus_filters.append("\n".join(entries))
            if len(entries) > 1:
                livestatus_filters[-1] += "\nOr: %d" % len(entries)

        if len(livestatus_filters) > 1:
            livestatus_filters.append("And: %d" % len(livestatus_filters))

        self._queried_livestatus_columns = list(columns_to_query)
        self._livestatus_command = "GET %s\nColumns: %s\n%s\n" % (
            self._livestatus_table,
            " ".join(self._queried_livestatus_columns),
            "\n".join(livestatus_filters),
        )

        # Limit number of results
        limit = config.quicksearch_dropdown_limit
        self._livestatus_command += "Cache: reload\nLimit: %d\nColumnHeaders: off" % (limit + 1)

    def _get_used_search_plugins(self):
        return [
            plugin for plugin_class in match_plugin_registry.values()
            for plugin in [plugin_class()]
            if plugin.is_used_for_table(self._livestatus_table, self._used_filters)
        ]

    # Returns the livestatus table fitting the given filters
    def _determine_livestatus_table(self):
        # Available tables
        # hosts / services / hostgroups / servicegroups

        # {table} -> {is_included_in_table}
        # Hostgroups -> Hosts -> Services
        # Servicegroups -> Services

        preferred_tables = []
        for shortname in self._used_filters.keys():
            plugin = self._get_plugin_with_shortname(shortname)
            preferred_tables.append(plugin.get_preferred_livestatus_table())

        table_to_query = ""
        if "services" in preferred_tables:
            table_to_query = "services"
        elif "servicegroups" in preferred_tables:
            if "hosts" in preferred_tables or "hostgroups" in preferred_tables:
                table_to_query = "services"
            else:
                table_to_query = "servicegroups"
        elif "hosts" in preferred_tables:
            table_to_query = "hosts"
        elif "hostgroups" in preferred_tables:
            table_to_query = "hostgroups"

        self._livestatus_table = table_to_query

    def _get_livestatus_default_columns(self):
        return {
            "services": ["description", "host_name"],
            "hosts": ["name"],
            "hostgroups": ["name"],
            "servicegroups": ["name"],
        }[self._livestatus_table]

    def get_search_url_params(self):
        exact_match = self.num_rows() == 1
        target_view = self._get_target_view(exact_match=exact_match)

        url_params = [("view_name", target_view), ("filled_in", "filter")]
        for plugin in self._used_search_plugins:
            match_info = plugin.get_matches(target_view,
                                            exact_match and self._rows[0] or None,
                                            self._livestatus_table,
                                            self._used_filters,
                                            rows=self._rows)
            if not match_info:
                continue
            _text, url_filters = match_info
            url_params.extend(url_filters)

        return url_params

    def create_result_elements(self):
        self._elements = []
        if not self._rows:
            return

        target_view = self._get_target_view()

        # Feed each row to the filters and let them add additional text/url infos
        for row in self._rows:
            entry = {"text_tokens": []}
            url_params = []
            skip_site = False
            for filter_shortname in self._used_filters:
                plugin = self._get_plugin_with_shortname(filter_shortname)

                if plugin.is_group_match():
                    skip_site = True

                match_info = plugin.get_matches(target_view, row, self._livestatus_table,
                                                self._used_filters)
                if not match_info:
                    continue
                text, url_filters = match_info
                url_params.extend(url_filters)
                entry["text_tokens"].append((plugin.get_filter_shortname(), text))

            url_tokens = [("view_name", target_view)] + url_params
            if not skip_site:
                url_tokens.append(("site", row.get("site")))
            entry["url"] = self._build_url(url_tokens, restore_regex=True)

            entry["raw_data"] = row
            self._elements.append(entry)

        self._generate_display_texts()

    def _get_target_view(self, exact_match=True):
        if exact_match:
            if self._livestatus_table == "hosts":
                return "host"
            elif self._livestatus_table == "services":
                return "allservices"
            elif self._livestatus_table == "hostgroups":
                return "hostgroup"
            elif self._livestatus_table == "servicegroups":
                return "servicegroup"
        else:
            if self._livestatus_table == "hosts":
                return "searchhost"
            elif self._livestatus_table == "services":
                return "searchsvc"
            elif self._livestatus_table == "hostgroups":
                return "hostgroups"
            elif self._livestatus_table == "servicegroups":
                return "svcgroups"

    def _generate_display_texts(self):
        for element in self._elements:
            if self._livestatus_table == "services":
                element["display_text"] = element["raw_data"]["description"]
            else:
                element["display_text"] = element["text_tokens"][0][1]

        if self._element_texts_unique():
            return

        # Some (ugly) special handling when the results are not unique
        # Whenever this happens we try to find a fitting second value

        if self._livestatus_table in ["hostgroups", "servicegroups"]:
            # Discard redundant hostgroups
            new_elements = []
            used_groups = set()
            for element in self._elements:
                if element["display_text"] in used_groups:
                    continue
                new_elements.append(element)
                used_groups.add(element["display_text"])
            self._elements = new_elements
        else:
            # Add additional info to the display text
            for element in self._elements:
                hostname = element["raw_data"].get("host_name", element["raw_data"].get("name"))
                if "&host_regex=" not in element["url"]:
                    element["url"] += "&host_regex=%s" % hostname

                for shortname, text in element["text_tokens"]:
                    if shortname in ["h", "al"] and text not in element["display_text"]:
                        element["display_text"] += " <b>%s</b>" % text
                        break
                else:
                    element["display_text"] += " <b>%s</b>" % hostname

    def _element_texts_unique(self):
        used_texts = set()
        for entry in self._elements:
            if entry["display_text"] in used_texts:
                return False
            used_texts.add(entry["display_text"])
        return True


class LivestatusQuicksearch(LivestatusSearchBase):
    def __init__(self, query):
        self._query = query
        self._search_objects = []  # Each of these objects do exactly one ls query
        super(LivestatusQuicksearch, self).__init__()

    def generate_dropdown_results(self):
        try:
            self._query_data()
        except TooManyRowsError as e:
            html.show_warning(e)

        self._evaluate_results()
        self._render_dropdown_elements()

    def generate_search_url(self):
        try:
            self._query_data()
        except TooManyRowsError:
            pass

        # Generate a search page for the topmost search_object with results
        url_params = []

        restore_regex = False
        for search_object in self._search_objects:
            if search_object.num_rows() > 0:
                url_params.extend(search_object.get_search_url_params())
                if search_object.num_rows() == 1:
                    restore_regex = True
                break
        else:
            url_params.extend([
                ("view_name", "allservices"),
                ("filled_in", "filter"),
                ("service_regex", self._query),
            ])

        return self._build_url(url_params, restore_regex=restore_regex)

    def _query_data(self):
        self._determine_search_objects()
        self._conduct_search()

    def _determine_search_objects(self):
        filter_names = {"%s" % x().get_filter_shortname() for x in match_plugin_registry.values()}
        filter_regex = "|".join(filter_names)

        # Goal: "((^| )(hg|h|sg|s|al|tg|ad):)"
        regex = "((^| )(%(filter_regex)s):)" % {"filter_regex": filter_regex}
        found_filters = []
        matches = re.finditer(regex, self._query)
        for match in matches:
            found_filters.append((match.group(1), match.start()))

        if found_filters:
            filter_spec = {}
            current_string = self._query
            for filter_type, offset in found_filters[-1::-1]:
                filter_text = _to_regex(current_string[offset + len(filter_type):]).strip()
                filter_name = filter_type.strip().rstrip(":")
                filter_spec.setdefault(filter_name, []).append(filter_text)
                current_string = current_string[:offset]
            self._search_objects.append(LivestatusSearchConductor(filter_spec, "continue"))
        else:
            # No explicit filters set.
            # Use configured quicksearch search order
            for (filter_name, filter_behaviour) in config.quicksearch_search_order:
                self._search_objects.append(
                    LivestatusSearchConductor({filter_name: [_to_regex(self._query)]},
                                              filter_behaviour))

    # Collect the raw data from livestatus
    def _conduct_search(self):
        total_rows = 0
        for idx, search_object in enumerate(self._search_objects):
            search_object.do_query()
            total_rows += search_object.num_rows()

            if total_rows > config.quicksearch_dropdown_limit:
                search_object.remove_rows_from_end(total_rows - config.quicksearch_dropdown_limit)
                raise TooManyRowsError(
                    _("More than %d results") % config.quicksearch_dropdown_limit)

            if search_object.row_limit_exceeded():
                raise TooManyRowsError(
                    _("More than %d results") % config.quicksearch_dropdown_limit)

            if search_object.num_rows() > 0 and search_object.get_filter_behaviour() != "continue":
                if search_object.get_filter_behaviour() == "finished_distinct":
                    # Discard all data of previous filters and break
                    for i in range(idx - 1, -1, -1):
                        self._search_objects[i].remove_rows_from_end(
                            config.quicksearch_dropdown_limit)
                break

    # Generates elements out of the raw data
    def _evaluate_results(self):
        for search_object in self._search_objects:
            search_object.create_result_elements()

    # Renders the elements
    def _render_dropdown_elements(self):
        # Show search topic if at least two search objects provide elements
        show_match_topics = len([x for x in self._search_objects if x.num_rows() > 0]) > 1

        for search_object in self._search_objects:
            if not search_object.num_rows():
                continue
            elements = search_object.get_elements()
            elements.sort(key=lambda x: x["display_text"])
            if show_match_topics:
                match_topic = search_object.get_match_topic()
                html.div(_("Results for %s") % match_topic, class_="topic")

            for entry in elements:
                html.a(entry["display_text"],
                       id="result_%s" % self._query,
                       href=entry["url"],
                       target="main")


def generate_results(query):
    quicksearch = LivestatusQuicksearch(query)
    quicksearch.generate_dropdown_results()


def generate_search_results(query):
    quicksearch = LivestatusQuicksearch(query)
    return quicksearch.generate_search_url()


#.
#   .--Search Plugins------------------------------------------------------.
#   |  ____                      _       ____  _             _             |
#   | / ___|  ___  __ _ _ __ ___| |__   |  _ \| |_   _  __ _(_)_ __  ___   |
#   | \___ \ / _ \/ _` | '__/ __| '_ \  | |_) | | | | |/ _` | | '_ \/ __|  |
#   |  ___) |  __/ (_| | | | (__| | | | |  __/| | |_| | (_| | | | | \__ \  |
#   | |____/ \___|\__,_|_|  \___|_| |_| |_|   |_|\__,_|\__, |_|_| |_|___/  |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+
#   | Realize the search mechanism to find objects via livestatus          |
#   '----------------------------------------------------------------------'


# TODO: Simplify code by making static things like _filter_shortname class members
# and it's getters class methods
class QuicksearchMatchPlugin(six.with_metaclass(abc.ABCMeta, object)):
    def __init__(self, supported_livestatus_tables, preferred_livestatus_table, filter_shortname):
        self._filter_shortname = filter_shortname
        self._supported_livestatus_tables = supported_livestatus_tables
        self._preferred_livestatus_table = preferred_livestatus_table
        super(QuicksearchMatchPlugin, self).__init__()

    def get_filter_shortname(self):
        return self._filter_shortname

    def get_preferred_livestatus_table(self):
        return self._preferred_livestatus_table

    def is_filter_set(self, used_filters):
        return self.get_filter_shortname() in used_filters

    def is_used_for_table(self, livestatus_table, used_filters):
        # Check if this filters handles the table at all
        if livestatus_table not in self._supported_livestatus_tables:
            return False

        if self.get_filter_shortname() not in used_filters:
            return False

        return True

    @abc.abstractmethod
    def get_match_topic(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_livestatus_columns(self, livestatus_table):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_livestatus_filters(self, livestatus_table, used_filters):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_matches(self, for_view, row, livestatus_table, used_filters, rows=None):
        raise NotImplementedError()

    def is_group_match(self):
        return False

    def _matches_regex(self, pattern, value):
        return re.match(pattern, value)

    def _create_textfilter_regex(self, used_filters):
        patterns = used_filters[self.get_filter_shortname()]
        if len(patterns) > 1:
            return "(%s)" % "|".join(patterns)
        return patterns[0]


class MatchPluginRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return QuicksearchMatchPlugin

    def plugin_name(self, plugin_class):
        return plugin_class.__name__


match_plugin_registry = MatchPluginRegistry()


@match_plugin_registry.register
class GroupMatchPlugin(QuicksearchMatchPlugin):
    def __init__(self, group_type=None, filter_shortname=None):
        super(GroupMatchPlugin, self).__init__(
            ["%sgroups" % group_type, "%ss" % group_type, "services"],
            "%sgroups" % group_type,
            filter_shortname,
        )
        self._group_type = group_type

    def is_group_match(self):
        return True

    def get_match_topic(self):
        if self._group_type == "host":
            return _("Hostgroup")
        return _("Servicegroup")

    def get_livestatus_columns(self, livestatus_table):
        if livestatus_table == "%sgroups" % self._group_type:
            return ["name"]
        return ["%s_groups" % self._group_type]

    def get_livestatus_filters(self, livestatus_table, used_filters):
        filter_lines = []
        filter_prefix = ""
        if livestatus_table == "%sgroups" % self._group_type:
            filter_prefix = "name ~~ "
        else:
            filter_prefix = "%s_groups >= " % self._group_type

        for entry in used_filters.get(self.get_filter_shortname()):
            filter_lines.append("Filter: %s%s" % (filter_prefix, entry))

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(self, for_view, row, livestatus_table, used_filters, rows=None):
        supported_views = {
            ### View name    url fieldname,                  key in row
            # Group domains (hostgroups, servicegroups)
            "hostgroup": ["hostgroup", "name"],
            "hostgroups": ["hostgroup_regex", "name"],
            "servicegroup": ["servicegroup", "name"],
            "svcgroups": ["servicegroup_regex", "name"],

            # Host/Service domain (hosts, services)
            "allservices": ["%sgroups" % self._group_type,
                            "%s_groups" % self._group_type],
            "searchsvc": [
                "%sgroups" % self._group_type, self._group_type == "service" and "groups" or
                "host_groups"
            ],
            "searchhost": [
                "%sgroups" % self._group_type, self._group_type == "service" and "groups" or
                "host_groups"
            ]
        }

        view_info = supported_views.get(for_view)
        if not view_info:
            return

        filter_name, row_fieldname = view_info
        if row:
            value = row.get(row_fieldname)
        else:
            value = used_filters.get(self.get_filter_shortname())

        if isinstance(value, list):
            value = "|".join(value)

        return value, [(filter_name, value)]


@match_plugin_registry.register
class ServiceMatchPlugin(QuicksearchMatchPlugin):
    def __init__(self):
        super(ServiceMatchPlugin, self).__init__(["services"], "services", "s")

    def get_match_topic(self):
        return _("Service Description")

    def get_livestatus_columns(self, livestatus_table):
        return ["service_description"]

    def get_livestatus_filters(self, livestatus_table, used_filters):
        filter_lines = []
        for entry in used_filters.get(self.get_filter_shortname()):
            filter_lines.append("Filter: service_description ~~ %s" % entry)

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(self, for_view, row, livestatus_table, used_filters, rows=None):
        supported_views = ["allservices", "searchsvc"]
        if for_view not in supported_views:
            return

        if row:
            field_value = row.get("description")
        else:
            field_value = self._create_textfilter_regex(used_filters)

        return field_value, [("service_regex", field_value)]


@match_plugin_registry.register
class HostMatchPlugin(QuicksearchMatchPlugin):
    def __init__(self, livestatus_field=None, filter_shortname=None):
        super(HostMatchPlugin, self).__init__(["hosts", "services"], "hosts", filter_shortname)
        self._livestatus_field = livestatus_field  # address, name or alias

    def get_match_topic(self):
        if self._livestatus_field == "name":
            return _("Hostname")
        elif self._livestatus_field == "address":
            return _("Hostaddress")
        return _("Hostalias")

    def _get_real_fieldname(self, livestatus_table):
        if livestatus_table != "hosts":
            return "host_%s" % self._livestatus_field
        return self._livestatus_field

    def get_livestatus_columns(self, livestatus_table):
        return [self._get_real_fieldname(livestatus_table), "host_name"]

    def get_livestatus_filters(self, livestatus_table, used_filters):
        filter_lines = []
        for entry in used_filters.get(self.get_filter_shortname()):
            filter_lines.append("Filter: %s ~~ %s" %
                                (self._get_real_fieldname(livestatus_table), entry))

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(self, for_view, row, livestatus_table, used_filters, rows=None):
        supported_views = {
            # View name     Filter name
            # Exact matches (always uses hostname as filter)
            "host": {
                "name": "host",
                "address": "host",
                "alias": "host"
            },
            "allservices": {
                "name": "host_regex",
                "address": "host_regex",
                "alias": "host_regex"
            },
            # Multi matches
            "searchhost": {
                "name": "host_regex",
                "address": "host_address",
                "alias": "hostalias"
            },
            "searchsvc": {
                "name": "host_regex",
                "address": "host_address",
                "alias": "hostalias"
            }
        }

        view_info = supported_views.get(for_view)
        if not view_info:
            return

        filter_name = view_info.get(self._livestatus_field)

        if row:
            field_value = row.get(self._get_real_fieldname(livestatus_table))
            hostname = row.get("host_name", row.get("name"))
            url_info = [(filter_name, hostname)]
        else:
            field_value = self._create_textfilter_regex(used_filters)
            url_info = [(filter_name, field_value)]
            if self._livestatus_field == "address":
                url_info.append(("host_address_prefix", "yes"))

        return field_value, url_info


@match_plugin_registry.register
class HosttagMatchPlugin(QuicksearchMatchPlugin):
    def __init__(self):
        super(HosttagMatchPlugin, self).__init__(["hosts", "services"], "hosts", "tg")

    def _get_hosttag_dict(self):
        lookup_dict = {}
        for tag_group in config.tags.tag_groups:
            for grouped_tag in tag_group.tags:
                lookup_dict[grouped_tag.id] = tag_group.id
        return lookup_dict

    def get_match_topic(self):
        return _("Hosttag")

    def get_livestatus_columns(self, livestatus_table):
        return ["tags"]

    def get_livestatus_filters(self, livestatus_table, used_filters):
        filter_lines = []

        if len(used_filters.get(self.get_filter_shortname())) > 3:
            raise MKGeneralException("You can only set up to three 'tg:' filters")

        for entry in used_filters.get(self.get_filter_shortname()):
            if ":" not in entry:
                # Be compatible to pre 1.6 filtering for some time (no
                # tag-group:tag-value, but tag-value only)
                filter_lines.append("Filter: tag_values >= %s" % livestatus.lqencode(entry))
                continue

            tag_key, tag_value = entry.split(":", 1)
            filter_lines.append("Filter: tags = %s %s" %
                                (livestatus.lqencode(tag_key), livestatus.lqencode(tag_value)))

        if len(filter_lines) > 1:
            filter_lines.append("And: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(self, for_view, row, livestatus_table, used_filters, rows=None):
        supported_views = {"searchhost": "host_regex", "host": "host"}

        filter_name = supported_views.get(for_view)
        if not filter_name:
            return

        if row:
            hostname = row.get("host_name", row.get("name"))
            return hostname, [(filter_name, hostname)]

        url_infos = []
        hosttag_to_group_dict = self._get_hosttag_dict()

        for idx, entry in enumerate(used_filters.get(self.get_filter_shortname())):
            if ":" not in entry and entry in hosttag_to_group_dict:
                # Be compatible to pre 1.6 filtering for some time (no
                # tag-group:tag-value, but tag-value only)
                tag_key, tag_value = hosttag_to_group_dict[entry], entry
            else:
                tag_key, tag_value = entry.split(":", 1)

            url_infos.append(("host_tag_%d_grp" % idx, tag_key))
            url_infos.append(("host_tag_%d_op" % idx, "is"))
            url_infos.append(("host_tag_%d_val" % idx, tag_value))

        return "", url_infos


@match_plugin_registry.register
class ServiceGroupMatchPlugin(GroupMatchPlugin):
    def __init__(self):
        super(ServiceGroupMatchPlugin, self).__init__(group_type="service", filter_shortname="sg")


@match_plugin_registry.register
class HostGroupMatchPlugin(GroupMatchPlugin):
    def __init__(self):
        super(HostGroupMatchPlugin, self).__init__(group_type="host", filter_shortname="hg")


@match_plugin_registry.register
class HostNameMatchPlugin(HostMatchPlugin):
    def __init__(self):
        super(HostNameMatchPlugin, self).__init__(livestatus_field="name", filter_shortname="h")


@match_plugin_registry.register
class HostAliasMatchPlugin(HostMatchPlugin):
    def __init__(self):
        super(HostAliasMatchPlugin, self).__init__(livestatus_field="alias", filter_shortname="al")


@match_plugin_registry.register
class HostAddressMatchPlugin(HostMatchPlugin):
    def __init__(self):
        super(HostAddressMatchPlugin, self).__init__(livestatus_field="address",
                                                     filter_shortname="ad")
