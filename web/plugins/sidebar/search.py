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

def render_searchform():
    html.open_div(id_="mk_side_search", class_="content_center", onclick="mkSearchClose();")
    html.input(id_="mk_side_search_field", type_="text", name="search", autocomplete="off")
    html.icon_button("#", _("Search"), "quicksearch", onclick="mkSearchButton();")
    html.close_div()
    html.div('', id_="mk_side_clear")
    html.javascript_file(html.javascript_filename_for_browser("search"))

sidebar_snapins["search"] = {
    "title":       _("Quicksearch"),
    "description": _("Interactive search field for direct access to hosts, services, host- and "\
                     "servicegroups.<br>You can use the following filters:<br> <i>h:</i> Host, <i>s:</i> Service<br> "\
                     "<i>hg:</i> Hostgroup, <i>sg:</i> Servicegroup<br><i>ad:</i> Address, <i>al:</i> Alias, <i>tg:</i> Hosttag"),
    "render":      render_searchform,
    "restart":     False,
    "allowed":     [ "user", "admin", "guest" ],
    "styles":      """

#mk_side_search {
    width: 232px;
    padding: 0;
}

#mk_side_clear {
    clear: both;
}

#mk_side_search img.iconbutton {
    width: 33px;
    height: 26px;
    margin-top: -25px;
    left: 196px;
    float: left;
    position: relative;
    z-index:100;
}

#mk_side_search img.iconbutton {
    opacity: 1;
    filter: alpha(opacity=100); /* For IE8 and earlier */
}

#mk_side_search img.iconbutton:hover {
    filter: grayscale(20%);
    -webkit-filter: grayscale(20%);
    -moz-filter: grayscale(20%);
    -ms-filter: grayscale(20%);
    -o-filter: grayscale(20%);
}

#mk_side_search input {
    margin:  0;
    padding: 0px 5px;
    font-size: 8pt;
    width: 194px;
    height: 25px;
    background-image: url("images/quicksearch_field_bg.png");
    background-repeat: no-repeat;
    -moz-border-radius: 0px;
    border-style: none;
    float: left;
}

#mk_side_search div.topic{
    font-size: 125%;
    margin-top:  3px;
    margin-left:  2px;
}

#mk_search_results {
    position: relative;
    float:left;
    border: 1px solid white;
    background-color: #DFDFDF;
    color: #000;
    font-size: 80%;
    width: 223px;
}

#mk_search_results a {
    display: block;
    color: #000;
    text-decoration: none;
    text-align: left;
    padding-left: 5px;
    width: 217px;
}

#mk_search_results a:hover, #mk_search_results a.active {
    background-color: #BFBFBF;
}

#mk_search_results div.error {
    padding: 2px;
    font-size: 9pt;
}

#mk_search_results div.warning {
    padding: 2px;
    font-size: 9pt;
}

"""
}

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


class QuicksearchMatchPlugin(object):
    def __init__(self, supported_livestatus_tables, preferred_livestatus_table, filter_shortname):
        self._filter_shortname  = filter_shortname
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


    def get_match_topic(self):
        raise NotImplementedError()


    def get_livestatus_columns(self, livestatus_table):
        raise NotImplementedError()


    def get_livestatus_filters(self, livestatus_table, used_filters):
        raise NotImplementedError()


    def get_matches(self, for_view, row, livestatus_table, used_filter, rows = None):
        raise NotImplementedError()


    def is_group_match(self):
        return False


    def _matches_regex(self, pattern, value):
        return re.match(pattern, value)


    def _create_textfilter_regex(self, used_filters):
        patterns = used_filters[self.get_filter_shortname()]
        if len(patterns) > 1:
            return "(%s)" % "|".join(patterns)
        else:
            return patterns[0]



class GroupMatchPlugin(QuicksearchMatchPlugin):
    def __init__(self, group_type = None, filter_shortname = None):
        super(GroupMatchPlugin, self).__init__(["%sgroups" % group_type, "%ss" % group_type, "services"],
                                                "%sgroups" % group_type,
                                                filter_shortname)
        self._group_type = group_type


    def is_group_match(self):
        return True


    def get_match_topic(self):
        if self._group_type == "host":
            return _("Hostgroup")
        else:
            return _("Servicegroup")


    def get_livestatus_columns(self, livestatus_table):
        if livestatus_table == "%sgroups" % self._group_type:
            return ["name"]
        else:
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


    def get_matches(self, for_view, row, livestatus_table, used_filters, rows = None):
        supported_views = {
            ### View name    url fieldname,                  key in row
            # Group domains (hostgroups, servicegroups)
            "hostgroup":    ["hostgroup",                    "name"],
            "hostgroups":   ["hostgroup_regex",              "name"],
            "servicegroup": ["servicegroup",                 "name"],
            "svcgroups":    ["servicegroup_regex",           "name"],

            # Host/Service domain (hosts, services)
            "allservices": ["%sgroups" % self._group_type,
                            "%s_groups" % self._group_type],
            "searchsvc":    ["%sgroups" % self._group_type ,
                             self._group_type == "service" and "groups" or "host_groups"],
            "searchhost":   ["%sgroups" % self._group_type ,
                             self._group_type == "service" and "groups" or "host_groups"]
        }

        view_info = supported_views.get(for_view)
        if not view_info:
            return

        filter_name, row_fieldname = view_info
        if row:
            value = row.get(row_fieldname)
        else:
            value = used_filters.get(self.get_filter_shortname())

        if type(value) == list:
            value = "|".join(value)

        return value, [(filter_name, value)]



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


    def get_matches(self, for_view, row, livestatus_table, used_filters, rows = None):
        supported_views = ["allservices", "searchsvc"]
        if for_view not in supported_views:
            return

        if row:
            field_value = row.get("description")
        else:
            field_value = self._create_textfilter_regex(used_filters)

        return field_value, [("service_regex", field_value)]



class HostMatchPlugin(QuicksearchMatchPlugin):
    def __init__(self, livestatus_field = None, filter_shortname = None):
        super(HostMatchPlugin, self).__init__(["hosts", "services"], "hosts", filter_shortname)
        self._livestatus_field = livestatus_field # address, name or alias


    def get_match_topic(self):
        if self._livestatus_field == "name":
            return _("Hostname")
        elif self._livestatus_field == "address":
            return _("Hostaddress")
        else:
            return _("Hostalias")


    def _get_real_fieldname(self, livestatus_table):
        if livestatus_table != "hosts":
            return "host_%s" % self._livestatus_field
        else:
            return self._livestatus_field


    def get_livestatus_columns(self, livestatus_table):
        return [self._get_real_fieldname(livestatus_table), "host_name"]


    def get_livestatus_filters(self, livestatus_table, used_filters):
        filter_lines = []
        for entry in used_filters.get(self.get_filter_shortname()):
            filter_lines.append("Filter: %s ~~ %s" % (self._get_real_fieldname(livestatus_table), entry))

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)


    def get_matches(self, for_view, row, livestatus_table, used_filters, rows = None):
        supported_views = {
            # View name     Filter name
            # Exact matches (always uses hostname as filter)
            "host":         {"name":    "host",
                             "address": "host",
                             "alias":   "host"},
            "allservices":  {"name":    "host_regex",
                             "address": "host_regex",
                             "alias":   "host_regex"},
            # Multi matches
            "searchhost":   {"name":    "host_regex",
                             "address": "host_address",
                             "alias":   "hostalias"},
            "searchsvc":    {"name":    "host_regex",
                             "address": "host_address",
                             "alias":   "hostalias"}
        }


        view_info = supported_views.get(for_view)
        if not view_info:
            return

        filter_name = view_info.get(self._livestatus_field)

        if row:
            field_value = row.get(self._get_real_fieldname(livestatus_table))
            hostname    = row.get("host_name", row.get("name"))
            url_info    = [(filter_name, hostname)]
        else:
            field_value = self._create_textfilter_regex(used_filters)
            url_info = [(filter_name, field_value)]
            if self._livestatus_field == "address":
                url_info.append(("host_address_prefix", "yes"))

        return field_value, url_info



class HosttagMatchPlugin(QuicksearchMatchPlugin):
    def __init__(self):
        super(HosttagMatchPlugin, self).__init__(["hosts", "services"], "hosts", "tg")


    def _get_hosttag_dict(self):
        lookup_dict = {}
        for entry in config.host_tag_groups():
            group, text, values = entry[:3]

            for value in values:
                lookup_dict[value[0]] = group
        return lookup_dict

    def get_match_topic(self):
        return _("Hosttag")


    def get_livestatus_columns(self, livestatus_table):
        return ["custom_variables"]


    def get_livestatus_filters(self, livestatus_table, used_filters):
        filter_lines = []

        if len(used_filters.get(self.get_filter_shortname())) > 3:
            raise MKGeneralException("You can only set up to three 'tg:' filters")

        for entry in used_filters.get(self.get_filter_shortname()):
            filter_lines.append("Filter: host_custom_variables ~ TAGS (^|[ ])%s($|[ ])" % lqencode(entry))

        if len(filter_lines) > 1:
            filter_lines.append("And: %d" % len(filter_lines))

        return "\n".join(filter_lines)


    def get_matches(self, for_view, row, livestatus_table, used_filters, rows = None):
        supported_views = {"searchhost": "host_regex",
                           "host":       "host"}

        filter_name = supported_views.get(for_view)
        if not filter_name:
            return

        if row:
            hostname = row.get("host_name", row.get("name"))
            return hostname, [(filter_name, hostname)]
        else:
            url_infos = []
            hosttag_to_group_dict = self._get_hosttag_dict()

            for idx, entry in enumerate(used_filters.get(self.get_filter_shortname())):
                if entry in hosttag_to_group_dict:
                    url_infos.append(("host_tag_%d_grp" % idx, hosttag_to_group_dict[entry]))
                    url_infos.append(("host_tag_%d_op"  % idx, "is"))
                    url_infos.append(("host_tag_%d_val" % idx, entry))

            return "", url_infos


quicksearch_match_plugins = []


quicksearch_match_plugins.append(
    ServiceMatchPlugin()
)

quicksearch_match_plugins.append(
    GroupMatchPlugin(group_type = "service", filter_shortname = "sg")
)

quicksearch_match_plugins.append(
    GroupMatchPlugin(group_type = "host",    filter_shortname = "hg")
)

quicksearch_match_plugins.append(
    HostMatchPlugin(livestatus_field = "name",    filter_shortname = "h")
)

quicksearch_match_plugins.append(
    HostMatchPlugin(livestatus_field = "alias",   filter_shortname = "al")
)

quicksearch_match_plugins.append(
    HostMatchPlugin(livestatus_field = "address", filter_shortname = "ad")
)

quicksearch_match_plugins.append(
    HosttagMatchPlugin()
)




