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

# =================================================================== #

#        _    ____ ___      ____                                      #
#       / \  |  _ \_ _|    |  _ \  ___   ___ _   _                    #
#      / _ \ | |_) | |_____| | | |/ _ \ / __| | | |                   #
#     / ___ \|  __/| |_____| |_| | (_) | (__| |_| |                   #
#    /_/   \_\_|  |___|    |____/ \___/ \___|\__,_|                   #
#                                                                     #
# =================================================================== #
#
# A painter computes from information from a data row HTML output and
# a CSS class for one display column. Please note, that there is no
# 1:1 relation between data columns and display columns. A painter can
# make use of more than one data columns. One example is the current
# service state. It uses the columns "service_state" and "has_been_checked".
#
# A painter is a python dictionary with the following keys:
#
# "title":   Title of the column to be displayed in the view editor
#            *and* in views as column header
# "short":   If the key is defined, it is used as column header in views
#            instead of the the title
# "columns": Livestatus columns this painter need. Multisite retrieves
#            only data columns declared in the painters, so make sure
#            you do not leave out something here.
# "paint":   The actual paint function
#
# The paint function gets one argument: A data row, which is a python
# dictionary representing one data object (host, service, ...). Its
# keys are the column names, its values the actual values from livestatus
# (typed: numbers are float or int, not string)
#
# The paint function must return a pair of two strings: The HTML code
# for painting the column and a CSS class for the TD of the column.
# That class is optional and set to "" in most cases. Currently CSS
# styles are not modular and all defined in check_mk.css. This will
# change in future.

import bi # Needed for BI Icon. For arkane reasons (ask htdocs/module.py) this
          # cannot be imported in views.py directly.

import cmk.paths
import cmk.man_pages as man_pages
from cmk.regex import regex
from cmk.defines import short_service_state_name, short_host_state_name
from lib import *

#   .--Painter Options-----------------------------------------------------.
#   |                   ____       _       _                               |
#   |                  |  _ \ __ _(_)_ __ | |_ ___ _ __                    |
#   |                  | |_) / _` | | '_ \| __/ _ \ '__|                   |
#   |                  |  __/ (_| | | | | | ||  __/ |                      |
#   |                  |_|   \__,_|_|_| |_|\__\___|_|                      |
#   |                                                                      |
#   |                   ___        _   _                                   |
#   |                  / _ \ _ __ | |_(_) ___  _ __  ___                   |
#   |                 | | | | '_ \| __| |/ _ \| '_ \/ __|                  |
#   |                 | |_| | |_) | |_| | (_) | | | \__ \                  |
#   |                  \___/| .__/ \__|_|\___/|_| |_|___/                  |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   | Painter options influence how painters render their data. Painter    |
#   | options are stored together with "refresh" and "columns" as "View    |
#   | options".                                                            |
#   '----------------------------------------------------------------------'

multisite_painter_options["pnp_timerange"] = {
    'valuespec' : Timerange(
        title = _("Graph time range"),
        default_value = None,
        include_time = True,
    )
}

multisite_painter_options["ts_format"] = {
    'valuespec': DropdownChoice(
        title = _("Time stamp format"),
        default_value = config.default_ts_format,
        choices = [
            ("mixed", _("Mixed")),
            ("abs",   _("Absolute")),
            ("rel",   _("Relative")),
            ("both",  _("Both")),
            ("epoch", _("Unix Timestamp (Epoch)")),
        ],
    )
}

multisite_painter_options["ts_date"] = {
    'valuespec' : DateFormat(),
}

multisite_painter_options["matrix_omit_uniform"] = {
    'valuespec' : DropdownChoice(
        title = _("Find differences..."),
        choices = [
            ( False, _("Always show all rows") ),
            ( True, _("Omit rows where all columns are identical") ),
        ]
    )
}

#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


# This helper function returns the value of the given custom var
def paint_custom_var(what, key, row, choices=None):
    if choices is None:
        choices = []

    if what:
        what += '_'

    custom_vars = dict(zip(row[what + "custom_variable_names"],
                           row[what + "custom_variable_values"]))

    if key in custom_vars:
        custom_val = custom_vars[key]
        if choices:
            custom_val = dict(choices).get(int(custom_val), custom_val)
        return key, custom_val

    return key, ""



def paint_nagios_link(row):
    # We need to use the Nagios-URL as configured
    # in sites.
    baseurl = config.site(row["site"])["url_prefix"] + "nagios/cgi-bin"
    url = baseurl + "/extinfo.cgi?host=" + html.urlencode(row["host_name"])
    svc = row.get("service_description")
    if svc:
        url += "&type=2&service=" + html.urlencode(svc)
        what = "service"
    else:
        url += "&type=1"
        what = "host"
    return "singleicon", "<a href=\"%s\">%s</a>" % \
        (url, html.render_icon('nagios', _('Show this %s in Nagios') % what))


def paint_age(timestamp, has_been_checked, bold_if_younger_than, mode=None, what='past'):
    if not has_been_checked:
        return "age", "-"

    if mode == None:
        mode = painter_options.get("ts_format")

    if mode == "epoch":
        return "", str(int(timestamp))

    if mode == "both":
        css, h1 = paint_age(timestamp, has_been_checked, bold_if_younger_than, "abs", what=what)
        css, h2 = paint_age(timestamp, has_been_checked, bold_if_younger_than, "rel", what=what)
        return css, "%s - %s" % (h1, h2)

    dateformat = painter_options.get("ts_date")
    age = time.time() - timestamp
    if mode == "abs" or \
        (mode == "mixed" and abs(age) >= 48 * 3600):
        return "age", time.strftime(dateformat + " %H:%M:%S", time.localtime(timestamp))

    warn_txt = ''
    output_format = "%s"
    if what == 'future' and age > 0:
        warn_txt = ' <b>%s</b>' % _('in the past!')
    elif what == 'past' and age < 0:
        warn_txt = ' <b>%s</b>' % _('in the future!')
    elif what == 'both' and age > 0:
        output_format = "%%s %s" % _("ago")


    # Time delta less than two days => make relative time
    if age < 0:
        age = -age
        prefix = "in "
    else:
        prefix = ""
    if age < bold_if_younger_than:
        age_class = "age recent"
    else:
        age_class = "age"

    return age_class, prefix + (output_format % age_human_readable(age)) + warn_txt


def paint_future_time(timestamp):
    if timestamp <= 0:
        return "", "-"
    else:
        return paint_age(timestamp, True, 0, what='future')

def paint_day(timestamp):
    return "", time.strftime("%A, %Y-%m-%d", time.localtime(timestamp))

#.
#   .--Icons---------------------------------------------------------------.
#   |                       ___                                            |
#   |                      |_ _|___ ___  _ __  ___                         |
#   |                       | |/ __/ _ \| '_ \/ __|                        |
#   |                       | | (_| (_) | | | \__ \                        |
#   |                      |___\___\___/|_| |_|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Deprecated in 1.2.7i1
multisite_icons = []

# Use this structure for new icons
multisite_icons_and_actions = {}

load_web_plugins('icons', globals())

def get_multisite_icons():
    icons = {}

    for icon_id, icon_config in multisite_icons_and_actions.items():
        icon = {
            "toplevel" : False,
            "sort_index" : 30,
        }
        icon.update(icon_config)
        icons[icon_id] = icon

    # multisite_icons has been deprecated, but to be compatible to old icon
    # plugins transform them to the new structure. We use part of the paint
    # function name as icon id.
    for icon_config in multisite_icons:
        icon = {
            "toplevel" : False,
            "sort_index" : 30,
        }
        icon.update(icon_config)
        icon_id = icon['paint'].__name__.replace('paint_', '')
        icons[icon_id] = icon

    # Now apply the user customized options
    for icon_id, cfg in config.builtin_icon_visibility.items():
        if icon_id in icons:
            if 'toplevel' in cfg:
                icons[icon_id]['toplevel'] = cfg['toplevel']
            if 'sort_index' in cfg:
                icons[icon_id]['sort_index'] = cfg['sort_index']

    return icons

def process_multisite_icons(what, row, tags, custom_vars, toplevel):
    icons = []
    for icon_id, icon in get_multisite_icons().items():
        if icon.get('type', 'icon') == 'icon':
            try:
                title      = None
                url        = None
                if icon['toplevel'] != toplevel:
                    continue

                sort_index = icon['sort_index']

                # In old versions, the icons produced html code directly. The new API
                # is that the icon functions need to return:
                # a) None          - nothing to be rendered
                # b) single string - the icon name (without .png)
                # c) tuple         - icon, title
                # d) triple        - icon, title, url
                try:
                    result = icon['paint'](what, row, tags, custom_vars)
                except Exception, e:
                    if config.debug:
                        raise
                    result = ("alert", "%s" % e)

                if result is None:
                    continue

                elif type(result) in [str, unicode, HTML]:

                    # TODO: This is handling the deprecated API with 1.2.7. Remove this one day.
                    if result[0] == '<':
                        # seems like an old format icon (html code). In regular rendering
                        # case (html), it can simply be appended to the output. Otherwise
                        # extract the icon name from icon images
                        if html.output_format == "html":
                            icons.append((sort_index, result))
                        else:
                            # Strip icon names out of HTML code that is generated by htmllib.render_icon()
                            for n in regex('<img src="([^"]*)"[^>]*>').findall("%s" % result):
                                if n.startswith("images/"):
                                    n = n[7:]
                                if n.startswith("icon_"):
                                    n = n[5:]
                                if n.endswith(".png"):
                                    n = n[:-4]
                                icons.append((sort_index, n.encode('utf-8'), None, None))
                        continue

                    else:
                        icon_name = result
                else:
                    if len(result) == 2:
                        icon_name, title = result
                    elif len(result) == 3:
                        icon_name, title, url = result
                icons.append((sort_index, icon_name, title, url))

            except Exception, e:
                import traceback
                icons.append((sort_index, 'Exception in icon plugin!<br />' + traceback.format_exc()))
    return icons


def process_custom_user_icons_and_actions(user_action_ids, toplevel):
    icons = []
    for id in user_action_ids:
        try:
            icon = config.user_icons_and_actions[id]
        except KeyError:
            continue # Silently skip not existing icons

        if icon.get('toplevel', False) == toplevel:
            sort_index = icon.get('sort_index', 15)
            icons.append((sort_index, icon['icon'], icon.get('title'), icon.get('url')))

    return icons


def get_icons(what, row, toplevel):
    host_custom_vars = dict(zip(row["host_custom_variable_names"],
                                row["host_custom_variable_values"]))

    if what != 'host':
        custom_vars = dict(zip(row[what+"_custom_variable_names"],
                               row[what+"_custom_variable_values"]))
    else:
        custom_vars = host_custom_vars

    # Extract needed custom variables
    tags = host_custom_vars.get('TAGS', '').split()
    user_action_ids = custom_vars.get('ACTIONS', '').split(',')

    # Icons is a list of triple or quintuplets with these elements:
    # (toplevel, sort_index, html_code)
    #  -> TODO: can be removed one day, handles deprecated icon API
    #  -> this can only happen for toplevel_icons and when output
    #     is written to HTML
    #  -> or when an exception occured
    # (toplevel, sort_index, icon_name, title, url)
    icons = process_multisite_icons(what, row, tags, host_custom_vars, toplevel)
    icons += process_custom_user_icons_and_actions(user_action_ids, toplevel)
    return sorted(icons, key = lambda i: i[0])


def replace_action_url_macros(url, what, row):
    url = url.replace('$HOSTNAME$', row['host_name']).replace('$HOSTADDRESS$', row['host_address'])
    if what == 'service':
        url = url.replace('$SERVICEDESC$', row['service_description'])
    return url


# Paint column with various icons. The icons use
# a plugin based mechanism so it is possible to
# register own icon "handlers".
# what: either "host" or "service"
# row: the data row of the host or service
def paint_icons(what, row):
    if not row["host_name"]:
        return "", ""# Host probably does not exist
    toplevel_icons = get_icons(what, row, toplevel=True)

    # In case of non HTML output, just return the top level icon names
    # as space separated string
    if html.output_format != 'html':
        return 'icons', ' '.join([ i[1] for i in toplevel_icons ])

    output = ''
    for icon in toplevel_icons:
        if len(icon) == 4:
            icon_name, title, url_spec = icon[1:]
            if url_spec:
                url, target_frame = sanitize_action_url(url_spec)
                url = replace_action_url_macros(url, what, row)

                onclick = ''
                if url.startswith('onclick:'):
                    onclick = url[8:]
                    url = 'javascript:void(0)'

                output += html.render_icon_button(url, title, icon_name,
                                onclick=onclick, target=target_frame, ty="icon")
            else:
                output += html.render_icon(icon_name, title)
        else:
            output += icon[1]

    return "icons", output


# toplevel may be
#  True to get only columns for top level icons
#  False to get only columns for dropdown menu icons
#  None to get columns for all active icons
def iconpainter_columns(what, toplevel):
    cols = set(['site',
                'host_name',
                'host_address',
                'host_custom_variable_names',
                'host_custom_variable_values' ])

    if what == 'service':
        cols.update([
            'service_description',
            'service_custom_variable_names',
            'service_custom_variable_values',
        ])

    for icon_id, icon in get_multisite_icons().items():
        if toplevel == None or toplevel == icon['toplevel']:
            if 'columns' in icon:
                cols.update([ what + '_' + c for c in icon['columns'] ])
            cols.update([ "host_" + c for c in icon.get("host_columns", [])])
            if what == "service":
                cols.update([ "service_" + c for c in icon.get("service_columns", [])])

    return cols

multisite_painters["service_icons"] = {
    "title"     : _("Service icons"),
    "short"     : _("Icons"),
    "printable" : False, # does not contain printable text
    "columns"   : lambda: iconpainter_columns("service", toplevel=None),
    "groupby"   : lambda row: "", # Do not account for in grouping
    "paint"     : lambda row: paint_icons("service", row)
}

multisite_painters["host_icons"] = {
    "title"     : _("Host icons"),
    "short"     : _("Icons"),
    "printable" : False, # does not contain printable text
    "columns"   : lambda: iconpainter_columns("host", toplevel=None),
    "groupby"   : lambda row: "", # Do not account for in grouping
    "paint"     : lambda row: paint_icons("host", row)
}


#.
#   .--Site----------------------------------------------------------------.
#   |                           ____  _ _                                  |
#   |                          / ___|(_) |_ ___                            |
#   |                          \___ \| | __/ _ \                           |
#   |                           ___) | | ||  __/                           |
#   |                          |____/|_|\__\___|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Column painters showing information about a site.                   |
#   '----------------------------------------------------------------------'

def paint_site_icon(row):
    if row.get("site") and config.use_siteicons:
        return None, "<img class=siteicon src=\"icons/site-%s-24.png\">" % row["site"]
    else:
        return None, ""

multisite_painters["site_icon"] = {
    "title"   : _("Site icon"),
    "short"   : "",
    "columns" : ["site"],
    "paint"   : paint_site_icon,
    "sorter"  : 'site',
}

multisite_painters["sitename_plain"] = {
    "title"   : _("Site ID"),
    "short"   : _("Site"),
    "columns" : ["site"],
    "paint"   : lambda row: (None, row["site"]),
    "sorter"  : 'site',
}

multisite_painters["sitealias"] = {
    "title"   : _("Site alias"),
    "columns" : ["site"],
    "paint"   : lambda row: (None, config.site(row["site"])["alias"]),
}



#.
#   .--Services------------------------------------------------------------.
#   |                ____                  _                               |
#   |               / ___|  ___ _ ____   _(_) ___ ___  ___                 |
#   |               \___ \ / _ \ '__\ \ / / |/ __/ _ \/ __|                |
#   |                ___) |  __/ |   \ V /| | (_|  __/\__ \                |
#   |               |____/ \___|_|    \_/ |_|\___\___||___/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Painters for services                                                |
#   '----------------------------------------------------------------------'

def paint_service_state_short(row):
    if row["service_has_been_checked"] == 1:
        state = str(row["service_state"])
        name = short_service_state_name(row["service_state"], "")
    else:
        state = "p"
        name = short_service_state_name(-1, "")

    if is_stale(row):
        state = str(state) + " stale"

    return "state svcstate state%s" % state, name


def paint_host_state_short(row, short=False):
    if row["host_has_been_checked"] == 1:
        state = row["host_state"]
        # A state of 3 is sent by livestatus in cases where no normal state
        # information is avaiable, e.g. for "DOWNTIMESTOPPED (UP)"
        name = short_host_state_name(row["host_state"], "")
    else:
        state = "p"
        name = _("PEND")

    if is_stale(row):
        state = str(state) + " stale"

    if short:
        name = name[0]

    return "state hstate hstate%s" % state, name


multisite_painters["service_nagios_link"] = {
    "title"   : _("Icon with link to service in Nagios GUI"),
    "short"   : "",
    "columns" : [ "site", "host_name", "service_description" ],
    "paint"   : paint_nagios_link
}

multisite_painters["service_state"] = {
    "title"   : _("Service state"),
    "short"   : _("State"),
    "columns" : ["service_has_been_checked","service_state"],
    "paint"   : paint_service_state_short,
    "sorter"  : 'svcstate',
}


multisite_painters["svc_plugin_output"] = {
    "title"   : _("Output of check plugin"),
    "short"   : _("Status detail"),
    "columns" : ["service_plugin_output"],
    "paint"   : lambda row: paint_stalified(row, format_plugin_output(row["service_plugin_output"], row)),
    "sorter"  : 'svcoutput',
}

multisite_painters["svc_long_plugin_output"] = {
    "title"   : _("Long output of check plugin (multiline)"),
    "short"   : _("Status detail"),
    "columns" : ["service_long_plugin_output"],
    "paint"   : lambda row: paint_stalified(row, format_plugin_output(row["service_long_plugin_output"], row).replace('\\n', '<br>').replace('\n', '<br>')),
}

multisite_painters["svc_perf_data"] = {
    "title" : _("Service performance data (source code)"),
    "short" : _("Perfdata"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_stalified(row, row["service_perf_data"])
}

def paint_service_metrics(row):
    translated_metrics = metrics.translate_perf_data(row["service_perf_data"],
                                                     row["service_check_command"])

    if row["service_perf_data"] and not translated_metrics:
        return "", _("Failed to parse performance data string: %s") % row["service_perf_data"]

    return "", metrics.render_metrics_table(translated_metrics, row["host_name"],
                                            row["service_description"])

multisite_painters["svc_metrics"] = {
    "title" : _("Service Metrics"),
    "short" : _("Metrics"),
    "columns" : [ "service_check_command", "service_perf_data"],
    "paint" : paint_service_metrics,
    "printable" : False,
}

def get_perfdata_nth_value(row, n, remove_unit = False):
    perfdata = row.get("service_perf_data")
    if not perfdata:
        return ''
    try:
        parts = perfdata.split()
        if len(parts) <= n:
            return "" # too few values in perfdata
        varname, rest = parts[n].split("=")
        number = rest.split(';')[0]
        # Remove unit. Why should we? In case of sorter (numeric)
        if remove_unit:
            while len(number) > 0 and not number[-1].isdigit():
                number = number[:-1]
        return number
    except Exception, e:
        return str(e)

def paint_perfdata_nth_value(row, n):
    return paint_stalified(row, get_perfdata_nth_value(row, n))

multisite_painters["svc_perf_val01"] = {
    "title" : _("Service performance data - value number  1"),
    "short" : _("Val. 1"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 0)
}

multisite_painters["svc_perf_val02"] = {
    "title" : _("Service performance data - value number  2"),
    "short" : _("Val. 2"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 1)
}

multisite_painters["svc_perf_val03"] = {
    "title" : _("Service performance data - value number  3"),
    "short" : _("Val. 3"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 2)
}

multisite_painters["svc_perf_val04"] = {
    "title" : _("Service performance data - value number  4"),
    "short" : _("Val. 4"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 3)
}

multisite_painters["svc_perf_val05"] = {
    "title" : _("Service performance data - value number  5"),
    "short" : _("Val. 5"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 4)
}

multisite_painters["svc_perf_val06"] = {
    "title" : _("Service performance data - value number  6"),
    "short" : _("Val. 6"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 5)
}

multisite_painters["svc_perf_val07"] = {
    "title" : _("Service performance data - value number  7"),
    "short" : _("Val. 7"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 6)
}

multisite_painters["svc_perf_val08"] = {
    "title" : _("Service performance data - value number  8"),
    "short" : _("Val. 8"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 7)
}

multisite_painters["svc_perf_val09"] = {
    "title" : _("Service performance data - value number  9"),
    "short" : _("Val. 9"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 8)
}

multisite_painters["svc_perf_val10"] = {
    "title" : _("Service performance data - value number 10"),
    "short" : _("Val. 10"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 9)
}

multisite_painters["svc_perf_firstval"] = {
    "title" : _("OBSOLETE - DO NOT USE THIS COLUMN"),
    "short" : _("Value"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 0)
}

multisite_painters["svc_check_command"] = {
    "title"   : _("Service check command"),
    "short"   : _("Check command"),
    "columns" : ["service_check_command"],
    "paint"   : lambda row: (None, html.attrencode(row["service_check_command"])),
}

multisite_painters["svc_check_command_expanded"] = {
    "title"   : _("Service check command expanded"),
    "short"   : _("Check command expanded"),
    "columns" : ["service_check_command_expanded"],
    "paint"   : lambda row: (None, html.attrencode(row["service_check_command_expanded"])),
}

multisite_painters["svc_contacts"] = {
    "title"   : _("Service contacts"),
    "short"   : _("Contacts"),
    "columns" : ["service_contacts"],
    "paint"   : lambda row: (None, ", ".join(row["service_contacts"])),
}

multisite_painters["svc_contact_groups"] = {
    "title"   : _("Service contact groups"),
    "short"   : _("Contact groups"),
    "columns" : ["service_contact_groups"],
    "paint"   : lambda row: (None, ", ".join(row["service_contact_groups"])),
}


multisite_painters["service_description"] = {
    "title"   : _("Service description"),
    "short"   : _("Service"),
    "columns" : ["service_description"],
    "paint"   : lambda row: (None, row["service_description"]),
    "sorter"  : 'svcdescr',
}

multisite_painters["service_display_name"] = {
    "title"   : _("Service alternative display name"),
    "short"   : _("Display name"),
    "columns" : ["service_display_name"],
    "paint"   : lambda row: (None, row["service_display_name"]),
    "sorter"  : 'svcdispname',
}

multisite_painters["svc_state_age"] = {
    "title"   : _("The age of the current service state"),
    "short"   : _("Age"),
    "columns" : [ "service_has_been_checked", "service_last_state_change" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["service_last_state_change"], row["service_has_been_checked"] == 1, 60 * 10),
    "sorter"  : "stateage",
}

def paint_checked(what, row):
    age = row[what + "_last_check"]
    if what == "service":
        cached_at = row["service_cached_at"]
        if cached_at:
            age = cached_at

    css, td = paint_age(age, row[what + "_has_been_checked"] == 1, 0)
    if is_stale(row):
        css += " staletime"
    return css, td

multisite_painters["svc_check_age"] = {
    "title"   : _("The time since the last check of the service"),
    "short"   : _("Checked"),
    "columns" : [ "service_has_been_checked", "service_last_check", "service_cached_at" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_checked("service", row),
}

def render_cache_info(what, row):
    cached_at = row["service_cached_at"]
    cache_interval = row["service_cache_interval"]
    cache_age = time.time() - cached_at

    text = _("Cache generated %s ago, cache interval: %s") % \
            (age_human_readable(cache_age), age_human_readable(cache_interval))

    if cache_interval:
        percentage = 100.0 * cache_age / cache_interval
        text += _(", elapsed cache lifespan: %s") % percent_human_redable(percentage)

    return text

def paint_cache_info(row):
    if not row["service_cached_at"]:
        return "", ""
    else:
        return "", render_cache_info("service", row)

multisite_painters["svc_check_cache_info"] = {
    "title"   : _("Cached agent data"),
    "short"   : _("Cached"),
    "columns" : [ "service_last_check", "service_cached_at", "service_cache_interval" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_cache_info(row),
}

multisite_painters["svc_next_check"] = {
    "title"   : _("The time of the next scheduled service check"),
    "short"   : _("Next check"),
    "columns" : [ "service_next_check" ],
    "paint"   : lambda row: paint_future_time(row["service_next_check"]),
}

multisite_painters["svc_last_time_ok"] = {
    "title"   : _("The last time the service was OK"),
    "short"   : _("Last OK"),
    "columns" : [ "service_last_time_ok", "service_has_been_checked" ],
    "paint"   : lambda row: paint_age(row["service_last_time_ok"], row["service_has_been_checked"] == 1, 60 * 10),
}

multisite_painters["svc_next_notification"] = {
    "title"   : _("The time of the next service notification"),
    "short"   : _("Next notification"),
    "columns" : [ "service_next_notification" ],
    "paint"   : lambda row: paint_future_time(row["service_next_notification"]),
}

multisite_painters["svc_last_notification"] = {
    "title"   : _("The time of the last service notification"),
    "short"   : _("last notification"),
    "columns" : [ "service_last_notification" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["service_last_notification"], row["service_last_notification"], 0),
}

multisite_painters['svc_notification_number'] = {
    "title"     : _("Service notification number"),
    "short"     : _("N#"),
    "columns"   : [ "service_current_notification_number" ],
    "paint"     : lambda row: ("", str(row["service_current_notification_number"])),
}


multisite_painters["svc_check_latency"] = {
    "title"   : _("Service check latency"),
    "short"   : _("Latency"),
    "columns" : [ "service_latency" ],
    "paint"   : lambda row: ("", "%.3f sec" % row["service_latency"]),
}

multisite_painters["svc_check_duration"] = {
    "title"   : _("Service check duration"),
    "short"   : _("Duration"),
    "columns" : [ "service_execution_time" ],
    "paint"   : lambda row: ("", "%.3f sec" % row["service_execution_time"]),
}

multisite_painters["svc_attempt"] = {
    "title"   : _("Current check attempt"),
    "short"   : _("Att."),
    "columns" : [ "service_current_attempt", "service_max_check_attempts" ],
    "paint"   : lambda row: (None, "%d/%d" % (row["service_current_attempt"], row["service_max_check_attempts"])),
}

multisite_painters["svc_normal_interval"] = {
    "title"   : _("Service normal check interval"),
    "short"   : _("Check int."),
    "columns" : [ "service_check_interval" ],
    "paint"   : lambda row: ("number", "%.0fs" % (row["service_check_interval"] * 60.0)),
}
multisite_painters["svc_retry_interval"] = {
    "title"   : _("Service retry check interval"),
    "short"   : _("Retry"),
    "columns" : [ "service_retry_interval" ],
    "paint"   : lambda row: ("number", "%.0fs" % (row["service_retry_interval"] * 60.0)),
}
multisite_painters["svc_check_interval"] = {
    "title"   : _("Service normal/retry check interval"),
    "short"   : _("Interval"),
    "columns" : [ "service_check_interval", "service_retry_interval" ],
    "paint"   : lambda row: (None, "%.0fs/%.0fs" % (
            row["service_check_interval"] * 60.0, row["service_retry_interval"] * 60.0)),
}

multisite_painters["svc_check_type"] = {
    "title"   : _("Service check type"),
    "short"   : _("Type"),
    "columns" : [ "service_check_type" ],
    "paint"   : lambda row: (None, row["service_check_type"] == 0 and "ACTIVE" or "PASSIVE"),
}

def paint_nagiosflag(row, field, bold_if_nonzero):
    value = row[field]
    yesno = {True: _("yes"), False: _("no")}[value != 0]
    if (value != 0) == bold_if_nonzero:
        return "badflag", yesno
    else:
        return "goodflag", yesno

multisite_painters["svc_in_downtime"] = {
    "title"   : _("Currently in downtime"),
    "short"   : _("Dt."),
    "columns" : [ "service_scheduled_downtime_depth" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_scheduled_downtime_depth", True),
}

multisite_painters["svc_in_notifper"] = {
    "title"   : _("In notification period"),
    "short"   : _("in notif. p."),
    "columns" : [ "service_in_notification_period" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_in_notification_period", False),
}

multisite_painters["svc_notifper"] = {
    "title"   : _("Service notification period"),
    "short"   : _("notif."),
    "columns" : [ "service_notification_period" ],
    "paint"   : lambda row: (None, row["service_notification_period"]),
}

multisite_painters["svc_check_period"] = {
    "title"   : _("Service check period"),
    "short"   : _("check."),
    "columns" : [ "service_check_period" ],
    "paint"   : lambda row: (None, row["service_check_period"]),
}

multisite_painters["svc_flapping"] = {
    "title"   : _("Service is flapping"),
    "short"   : _("Flap"),
    "columns" : [ "service_is_flapping" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_is_flapping", True),
}

multisite_painters["svc_notifications_enabled"] = {
    "title"   : _("Service notifications enabled"),
    "short"   : _("Notif."),
    "columns" : [ "service_notifications_enabled" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_notifications_enabled", False),
}

multisite_painters["svc_is_active"] = {
    "title"   : _("Service is active"),
    "short"   : _("Active"),
    "columns" : [ "service_active_checks_enabled" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_active_checks_enabled", None),
}

def paint_service_group_memberlist(row):
    links = []
    for group in row["service_groups"]:
        link = "view.py?view_name=servicegroup&servicegroup=" + group
        links.append('<a href="%s">%s</a>' % (link, group))
    return "", ", ".join(links)

multisite_painters["svc_group_memberlist"] = {
    "title"   : _("Service groups the service is member of"),
    "short"   : _("Groups"),
    "columns" : [ "service_groups" ],
    "paint"   : paint_service_group_memberlist,
}

def paint_time_graph(row, cell):
    if metrics.cmk_graphs_possible(row["site"]):
        return paint_time_graph_cmk(row, cell)
    else:
        return paint_time_graph_pnp(row)


def time_graph_params():
    try:
        return metrics.vs_graph_render_options()
    except AttributeError:
        return None # The method is only available in CEE


def paint_time_graph_cmk(row, cell, show_timeranges=False):
    graph_identification = (
        "template", {
            "site"                : row["site"],
            "host_name"           : row["host_name"],
            "service_description" : row.get("service_description", "_HOST_"),
    })
    graph_data_range = { "time_range" : get_graph_timerange_from_painter_options() }

    # Load the graph render options from
    # a) the painter parameters configured in the view
    # b) the painter options set per user and view
    graph_render_options = cell.painter_parameters().copy()

    options = painter_options.get_without_default("graph_render_options")
    if options != None:
        graph_render_options.update(options)
        del graph_render_options["set_default_time_range"]

    if html.is_mobile():
        graph_render_options.update({
            "interaction"   : False,
            "show_controls" : False,
            # Would be much better to autodetect the possible size (like on dashboard)
            "size"          : (50, 20), # ex
        })

    if "host_metrics" in row:
        available_metrics = row["host_metrics"]
        perf_data = row["host_perf_data"]
    else:
        available_metrics = row["service_metrics"]
        perf_data = row["service_perf_data"]

    if not available_metrics and perf_data:
        return "", _("No historic metrics recorded but performance data is available. "
                     "Maybe performance data processing is disabled.")

    return "", metrics.render_graphs_from_specification_html(
            graph_identification,
            graph_data_range,
            graph_render_options,
            show_timeranges)


def get_graph_timerange_from_painter_options():
    value = painter_options.get("pnp_timerange")
    vs = painter_options.get_valuespec_of("pnp_timerange")
    return map(int, vs.compute_range(value)[0])


def paint_time_graph_pnp(row):
    sitename = row["site"]
    host = row["host_name"]
    service = row.get("service_description", "_HOST_")

    container_id = "%s_%s_%s_graph" % (sitename, host, service)
    url_prefix = config.site(sitename)["url_prefix"]
    pnp_url = url_prefix + "pnp4nagios/"
    if display_options.enabled(display_options.X):
        with_link = 'true'
    else:
        with_link = 'false'

    pnp_timerange = painter_options.get("pnp_timerange")

    pnpview = '1'
    from_ts, to_ts = 'null', 'null'
    if pnp_timerange != None:
        if pnp_timerange[0] != 'pnp_view':
            from_ts, to_ts = get_graph_timerange_from_painter_options()
        else:
            pnpview = pnp_timerange[1]

    return "pnpgraph", "<div id=\"%s\"></div>" \
                       "<script>render_pnp_graphs('%s', '%s', '%s', '%s', '%s', '%s', '%s', %s, '%s', %s, %s)</script>" % \
                          (container_id, container_id, sitename, host, service, pnpview,
                           config.url_prefix() + "check_mk/", pnp_url, with_link, _('Add this graph to...'), from_ts, to_ts)


multisite_painters["svc_pnpgraph" ] = {
    "title"   : _("Service Graphs"),
    "columns" : [ "host_name", "service_description", "service_perf_data", "service_metrics", "service_check_command" ],
    "options" : [ "pnp_timerange" ],
    "paint"   : paint_time_graph,
    "printable" : "time_graph",
    "params"  : time_graph_params,
}


def paint_check_man_page(row):
    command = row["service_check_command"]
    if not command.startswith("check_mk-"):
        return "", ""
    checktype = command[9:]

    page = man_pages.load_man_page(checktype)
    if page is None:
        return "", _("Man page %s not found.") % checktype

    description = page["header"]["description"]
    return "", description.replace("<", "&lt;") \
                          .replace(">", "&gt;") \
                          .replace("{", "<b>") \
                          .replace("}", "</b>") \
                          .replace("&lt;br&gt;", "<br>")

multisite_painters["check_manpage"] = {
    "title"   : _("Check manual (for Check_MK based checks)"),
    "short"   : _("Manual"),
    "columns" : [ "service_check_command" ],
    "paint"   : paint_check_man_page,
}


def paint_comments(prefix, row):
    comments = row[ prefix + "comments_with_info"]
    text = ", ".join(["<i>%s</i>: %s" % (a, html.attrencode(c)) for (id, a, c) in comments ])
    return "", text

multisite_painters["svc_comments"] = {
    "title"   : _("Service Comments"),
    "short"   : _("Comments"),
    "columns" : [ "service_comments_with_info" ],
    "paint"   : lambda row: paint_comments("service_", row)
}

multisite_painters["svc_acknowledged"] = {
    "title"   : _("Service problem acknowledged"),
    "short"   : _("Ack"),
    "columns" : ["service_acknowledged"],
    "paint"   : lambda row: paint_nagiosflag(row, "service_acknowledged", False),
}

def notes_matching_pattern_entries(dirs, item):
    from fnmatch import fnmatch
    matching = []
    for dir in dirs:
        if os.path.isdir(dir):
            entries = filter(lambda d: d[0] != '.', os.listdir(dir))
            entries.sort()
            entries.reverse()
            for pattern in entries:
                if pattern[0] == '.':
                    continue
                if fnmatch(item, pattern):
                    matching.append(dir + "/" + pattern)
    return matching

def paint_custom_notes(what, row):
    host = row["host_name"]
    svc = row.get("service_description")
    if what == "service":
        notes_dir = cmk.paths.default_config_dir + "/notes/services"
        dirs = notes_matching_pattern_entries([notes_dir], host)
        item = svc
    else:
        dirs = [ cmk.paths.default_config_dir + "/notes/hosts" ]
        item = host

    files = notes_matching_pattern_entries(dirs, item)
    files.sort()
    files.reverse()
    contents = []
    def replace_tags(text):
        sitename = row["site"]
        url_prefix = config.site(sitename)["url_prefix"]
        return text\
            .replace('$URL_PREFIX$',     url_prefix)\
            .replace('$SITE$',           sitename)\
            .replace('$HOSTNAME$',       host)\
	    .replace('$HOSTNAME_LOWER$', host.lower())\
            .replace('$HOSTNAME_UPPER$', host.upper())\
            .replace('$HOSTNAME_TITLE$', host[0].upper() + host[1:].lower())\
            .replace('$HOSTADDRESS$',    row["host_address"])\
            .replace('$SERVICEOUTPUT$',  row.get("service_plugin_output", ""))\
            .replace('$HOSTOUTPUT$',     row.get("host_plugin_output", ""))\
            .replace('$SERVICEDESC$',    row.get("service_description", ""))

    for f in files:
        contents.append(replace_tags(unicode(file(f).read(), "utf-8").strip()))
    return "", "<hr>".join(contents)

multisite_painters["svc_custom_notes"] = {
    "title"   : _("Custom services notes"),
    "short"   : _("Notes"),
    "columns" : [ "host_name", "host_address", "service_description", "service_plugin_output" ],
    "paint"   : lambda row: paint_custom_notes("service", row),
}

multisite_painters["svc_staleness"] = {
    "title"   : _("Service staleness value"),
    "short"   : _("Staleness"),
    "columns" : ["service_staleness"],
    "paint"   : lambda row: ('', '%0.2f' % row.get('service_staleness', 0)),
}

def paint_is_stale(row):
    if is_stale(row):
        return "badflag", _('yes')
    else:
        return "goodflag", _('no')

multisite_painters["svc_is_stale"] = {
    "title"   : _("Service is stale"),
    "short"   : _("Stale"),
    "columns" : ["service_staleness"],
    "paint"   : paint_is_stale,
    "sorter"  : 'svc_staleness',
}

multisite_painters["svc_servicelevel"] = {
    "title"   : _("Service service level"),
    "short"   : _("Service Level"),
    "columns" : [ "service_custom_variable_names", "service_custom_variable_values" ],
    "paint"   : lambda row: paint_custom_var('service', 'EC_SL', row,
                            config.mkeventd_service_levels),
    "sorter"  : 'servicelevel',
}

def paint_custom_vars(what, row, blacklist=None):
    if blacklist is None:
        blacklist = []

    items = row[what + "_custom_variables"].items()
    items.sort()
    rows = []
    for varname, value in items:
        if varname not in blacklist:
            rows.append(html.render_tr(html.render_td(varname) + html.render_td(value)))
    return '', "%s" % html.render_table(HTML().join(rows))

multisite_painters["svc_custom_vars"] = {
    "title"   : _("Service custom variables"),
    "columns" : [ "service_custom_variables" ],
    "groupby" : lambda row: tuple(row["service_custom_variables"].items()),
    "paint"   : lambda row: paint_custom_vars('service', row),
}


#.
#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Painters for hosts                                                   |
#   '----------------------------------------------------------------------'


multisite_painters["host_state"] = {
    "title"   : _("Host state"),
    "short"   : _("state"),
    "columns" : ["host_has_been_checked","host_state"],
    "paint"   : paint_host_state_short,
    "sorter"  : 'hoststate',
}

multisite_painters["host_state_onechar"] = {
    "title"   : _("Host state (first character)"),
    "short"   : _("S."),
    "columns" : ["host_has_been_checked","host_state"],
    "paint"   : lambda row: paint_host_state_short(row, True),
    "sorter"  : 'hoststate',
}

multisite_painters["host_plugin_output"] = {
    "title"   : _("Output of host check plugin"),
    "short"   : _("Status detail"),
    "columns" : ["host_plugin_output"],
    "paint"   : lambda row: (None, row["host_plugin_output"]),
}

multisite_painters["host_perf_data"] = {
    "title"   : _("Host performance data"),
    "short"   : _("Performance data"),
    "columns" : ["host_perf_data"],
    "paint"   : lambda row: (None, row["host_perf_data"]),
}

multisite_painters["host_check_command"] = {
    "title"   : _("Host check command"),
    "short"   : _("Check command"),
    "columns" : ["host_check_command"],
    "paint"   : lambda row: (None, row["host_check_command"]),
}

multisite_painters["host_check_command_expanded"] = {
    "title"   : _("Host check command expanded"),
    "short"   : _("Check command expanded"),
    "columns" : ["host_check_command_expanded"],
    "paint"   : lambda row: (None, row["host_check_command_expanded"]),
}

multisite_painters["host_state_age"] = {
    "title"   : _("The age of the current host state"),
    "short"   : _("Age"),
    "columns" : [ "host_has_been_checked", "host_last_state_change" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["host_last_state_change"], row["host_has_been_checked"] == 1, 60 * 10),
}

multisite_painters["host_check_age"] = {
    "title"   : _("The time since the last check of the host"),
    "short"   : _("Checked"),
    "columns" : [ "host_has_been_checked", "host_last_check" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_checked("host", row),
}

multisite_painters["host_next_check"] = {
    "title"   : _("The time of the next scheduled host check"),
    "short"   : _("Next check"),
    "columns" : [ "host_next_check" ],
    "paint"   : lambda row: paint_future_time(row["host_next_check"]),
}

multisite_painters["host_next_notification"] = {
    "title"   : _("The time of the next host notification"),
    "short"   : _("Next notification"),
    "columns" : [ "host_next_notification" ],
    "paint"   : lambda row: paint_future_time(row["host_next_notification"]),
}

multisite_painters["host_last_notification"] = {
    "title"   : _("The time of the last host notification"),
    "short"   : _("last notification"),
    "columns" : [ "host_last_notification" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["host_last_notification"], row["host_last_notification"], 0),
}

multisite_painters["host_check_latency"] = {
    "title"   : _("Host check latency"),
    "short"   : _("Latency"),
    "columns" : [ "host_latency" ],
    "paint"   : lambda row: ("", "%.3f sec" % row["host_latency"]),
}

multisite_painters["host_check_duration"] = {
    "title"   : _("Host check duration"),
    "short"   : _("Duration"),
    "columns" : [ "host_execution_time" ],
    "paint"   : lambda row: ("", "%.3f sec" % row["host_execution_time"]),
}

multisite_painters["host_attempt"] = {
    "title"   : _("Current host check attempt"),
    "short"   : _("Att."),
    "columns" : [ "host_current_attempt", "host_max_check_attempts" ],
    "paint"   : lambda row: (None, "%d/%d" % (row["host_current_attempt"], row["host_max_check_attempts"])),
}

multisite_painters["host_normal_interval"] = {
    "title"   : _("Normal check interval"),
    "short"   : _("Check int."),
    "columns" : [ "host_check_interval" ],
    "paint"   : lambda row: (None, "%.0fs" % (row["host_check_interval"] * 60.0)),
}
multisite_painters["host_retry_interval"] = {
    "title"   : _("Retry check interval"),
    "short"   : _("Retry"),
    "columns" : [ "host_retry_interval" ],
    "paint"   : lambda row: (None, "%.0fs" % (row["host_retry_interval"] * 60.0)),
}
multisite_painters["host_check_interval"] = {
    "title"   : _("Normal/retry check interval"),
    "short"   : _("Interval"),
    "columns" : [ "host_check_interval", "host_retry_interval" ],
    "paint"   : lambda row: (None, "%.0fs/%.0fs" % (
            row["host_check_interval"] * 60.0, row["host_retry_interval"] * 60.0)),
}

multisite_painters["host_check_type"] = {
    "title"   : _("Host check type"),
    "short"   : _("Type"),
    "columns" : [ "host_check_type" ],
    "paint"   : lambda row: (None, row["host_check_type"] == 0 and "ACTIVE" or "PASSIVE"),
}

multisite_painters["host_in_notifper"] = {
    "title"   : _("Host in notif. period"),
    "short"   : _("in notif. p."),
    "columns" : [ "host_in_notification_period" ],
    "paint"   : lambda row: paint_nagiosflag(row, "host_in_notification_period", False),
}

multisite_painters["host_notifper"] = {
    "title"   : _("Host notification period"),
    "short"   : _("notif."),
    "columns" : [ "host_notification_period" ],
    "paint"   : lambda row: (None, row["host_notification_period"]),
}

multisite_painters['host_notification_number'] = {
    "title"     : _("Host notification number"),
    "short"     : _("N#"),
    "columns"   : [ "host_current_notification_number" ],
    "paint"     : lambda row: ("", str(row["host_current_notification_number"])),
}

multisite_painters["host_flapping"] = {
    "title"   : _("Host is flapping"),
    "short"   : _("Flap"),
    "columns" : [ "host_is_flapping" ],
    "paint"   : lambda row: paint_nagiosflag(row, "host_is_flapping", True),
}

multisite_painters["host_is_active"] = {
    "title"   : _("Host is active"),
    "short"   : _("Active"),
    "columns" : [ "host_active_checks_enabled" ],
    "paint"   : lambda row: paint_nagiosflag(row, "host_active_checks_enabled", None),
}
multisite_painters["host_notifications_enabled"] = {
    "title"   : _("Host notifications enabled"),
    "short"   : _("Notif."),
    "columns" : [ "host_notifications_enabled" ],
    "paint"   : lambda row: paint_nagiosflag(row, "host_notifications_enabled", False),
}

multisite_painters["host_pnpgraph" ] = {
    "title"   : _("Host graph"),
    "short"   : _("Graph"),
    "columns" : [ "host_name", "host_perf_data", "host_metrics", "host_check_command" ],
    "options" : [ 'pnp_timerange' ],
    "paint"   : paint_time_graph,
    "printable" : "time_graph",
    "params"  : time_graph_params,
}

def paint_host_black(row):
    state = row["host_state"]
    if state != 0:
        return "nobr", "<div class=hostdown>%s</div>" % row["host_name"]
    else:
        return "nobr", row["host_name"]

multisite_painters["host_black"] = {
    "title"   : _("Hostname, red background if down or unreachable"),
    "short"   : _("Host"),
    "columns" : ["site", "host_name", "host_state"],
    "paint"   : paint_host_black,
    "sorter"  : 'site_host',
}

def paint_host_black_with_link_to_old_nagios_services(row):
    host = row["host_name"]
    baseurl = config.site(row["site"])["url_prefix"] + "nagios/cgi-bin"
    url = baseurl + "/status.cgi?host=" + html.urlencode(host)
    state = row["host_state"]
    if state != 0:
        return None, '<div class=hostdown><a href="%s">%s</a></div>' % (url, host)
    else:
        return None, '<a href="%s">%s</a>' % (url, host)


multisite_painters["host_black_nagios"] = {
    "title"   : _("Hostname, red background if down, link to Nagios services"),
    "short"   : _("Host"),
    "columns" : ["site", "host_name", "host_state"],
    "paint"   : paint_host_black_with_link_to_old_nagios_services,
    "sorter"  : 'site_host',
}


multisite_painters["host_nagios_link"] = {
    "title"   : _("Icon with link to host to Nagios GUI"),
    "short"   : "",
    "columns" : [ "site", "host_name" ],
    "paint"   : paint_nagios_link,
}

def paint_host_with_state(row):
    if row["host_has_been_checked"]:
        state = row["host_state"]
    else:
        state = "p"
    if state != 0:
        return "state hstate hstate%s" % state, row["host_name"]
    else:
        return "nobr", row["host_name"]

multisite_painters["host_with_state"] = {
    "title"   : _("Hostname, marked red if down"),
    "short"   : _("Host"),
    "columns" : ["site", "host_name", "host_state", "host_has_been_checked" ],
    "paint"   : paint_host_with_state,
    "sorter"  : 'site_host',
}

multisite_painters["host"] = {
    "title"   : _("Hostname"),
    "short"   : _("Host"),
    "columns" : ["host_name"],
    "paint"   : lambda row: ("nobr", row["host_name"]),
    "sorter"  : 'site_host',
}

multisite_painters["alias"] = {
    "title"   : _("Host alias"),
    "short"   : _("Alias"),
    "columns" : ["host_alias"],
    "paint"   : lambda row: ("", row["host_alias"]),
}

multisite_painters["host_address"] = {
    "title"   : _("Host address (Primary)"),
    "short"   : _("IP address"),
    "columns" : ["host_address"],
    "paint"   : lambda row: ("", row["host_address"]),
}

multisite_painters["host_ipv4_address"] = {
    "title"   : _("Host address (IPv4)"),
    "short"   : _("IPv4 address"),
    "columns" : [ "host_custom_variable_names", "host_custom_variable_values" ],
    "paint"   : lambda row: paint_custom_var('host', 'ADDRESS_4', row),
}

multisite_painters["host_ipv6_address"] = {
    "title"   : _("Host address (IPv6)"),
    "short"   : _("IPv6 address"),
    "columns" : [ "host_custom_variable_names", "host_custom_variable_values" ],
    "paint"   : lambda row: paint_custom_var('host', 'ADDRESS_6', row),
}


def paint_host_addresses(row):
    custom_vars = dict(zip(row["host_custom_variable_names"],
                           row["host_custom_variable_values"]))

    if custom_vars.get("ADDRESS_FAMILY", "4") == "4":
        primary   = custom_vars.get("ADDRESS_4", "")
        secondary = custom_vars.get("ADDRESS_6", "")
    else:
        primary   = custom_vars.get("ADDRESS_6", "")
        secondary = custom_vars.get("ADDRESS_4", "")

    if secondary:
        secondary = " (%s)" % secondary
    return "", primary + secondary


multisite_painters["host_addresses"] = {
    "title"   : _("Host addresses"),
    "short"   : _("IP addresses"),
    "columns" : [ "host_address", "host_custom_variable_names", "host_custom_variable_values" ],
    "paint"   : paint_host_addresses,
}

multisite_painters["host_address_family"] = {
    "title"   : _("Host address family (Primary)"),
    "short"   : _("Address family"),
    "columns" : [ "host_custom_variable_names", "host_custom_variable_values" ],
    "paint"   : lambda row: paint_custom_var('host', 'ADDRESS_FAMILY', row),
}


def paint_host_address_families(row):
    custom_vars = dict(zip(row["host_custom_variable_names"],
                           row["host_custom_variable_values"]))

    primary = custom_vars.get("ADDRESS_FAMILY", "4")

    families = [primary]
    if primary == "6" and custom_vars.get("ADDRESS_4"):
        families.append("4")
    elif primary == "4" and custom_vars.get("ADDRESS_6"):
        families.append("6")

    return "", ", ".join(families)


multisite_painters["host_address_families"] = {
    "title"   : _("Host address families"),
    "short"   : _("Address families"),
    "columns" : [ "host_custom_variable_names", "host_custom_variable_values" ],
    "paint"   : paint_host_address_families,
}

def paint_svc_count(id, count):
    if count > 0:
        return "count svcstate state%s" % id, str(count)
    else:
        return "count svcstate statex", "0"

def paint_host_count(id, count):
    if count > 0:
        if id != None:
            return "count hstate hstate%s" % id, str(count)
        else: # pending
            return "count hstate hstatep", str(count)

    else:
        return "count hstate hstatex", "0"

multisite_painters["num_services"] = {
    "title"   : _("Number of services"),
    "short"   : "",
    "columns" : [ "host_num_services" ],
    "paint"   : lambda row: (None, str(row["host_num_services"])),
}

multisite_painters["num_services_ok"] = {
    "title"   : _("Number of services in state OK"),
    "short"   : _("OK"),
    "columns" : [ "host_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["host_num_services_ok"]),
}

multisite_painters["num_problems"] = {
    "title"   : _("Number of problems"),
    "short"   : _("Pro."),
    "columns" : [ "host_num_services", "host_num_services_ok", "host_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count('s', row["host_num_services"] - row["host_num_services_ok"] - row["host_num_services_pending"]),
}

multisite_painters["num_services_warn"] = {
    "title"   : _("Number of services in state WARN"),
    "short"   : _("Wa"),
    "columns" : [ "host_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["host_num_services_warn"]),
}

multisite_painters["num_services_crit"] = {
    "title"   : _("Number of services in state CRIT"),
    "short"   : _("Cr"),
    "columns" : [ "host_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["host_num_services_crit"]),
}

multisite_painters["num_services_unknown"] = {
    "title"   : _("Number of services in state UNKNOWN"),
    "short"   : _("Un"),
    "columns" : [ "host_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["host_num_services_unknown"]),
}

multisite_painters["num_services_pending"] = {
    "title"   : _("Number of services in state PENDING"),
    "short"   : _("Pd"),
    "columns" : [ "host_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["host_num_services_pending"]),
}

def paint_service_list(row, columnname):
    h = "<div class=objectlist>"
    def sort_key(entry):
        if columnname.startswith("servicegroup"):
            return entry[0].lower(), entry[1].lower()
        else:
            return entry[0].lower()

    for entry in sorted(row[columnname], key = sort_key):
        if columnname.startswith("servicegroup"):
            host, svc, state, checked = entry
            text = host + " ~ " + svc
        else:
            svc, state, checked = entry
            host = row["host_name"]
            text = svc
        link = "view.py?view_name=service&site=%s&host=%s&service=%s" % (
                html.urlencode(row["site"]),
                html.urlencode(host),
                html.urlencode(svc))
        if checked:
            css = "state%d" % state
        else:
            css = "statep"
        h += "<div class=\"%s\"><a href=\"%s\">%s</a></div>" % (css, link, text)
    h += "</div>"
    return "", h

multisite_painters["host_services"] = {
    "title"   : _("Services colored according to state"),
    "short"   : _("Services"),
    "columns" : [ "host_name", "host_services_with_state" ],
    "paint"   : lambda row: paint_service_list(row, "host_services_with_state"),
}

multisite_painters["host_parents"] = {
    "title"   : _("Host's parents"),
    "short"   : _("Parents"),
    "columns" : [ "host_parents" ],
    "paint"   : lambda row: paint_host_list(row["site"], row["host_parents"]),
}

multisite_painters["host_childs"] = {
    "title"   : _("Host's children"),
    "short"   : _("children"),
    "columns" : [ "host_childs" ],
    "paint"   : lambda row: paint_host_list(row["site"], row["host_childs"]),
}

def paint_host_group_memberlist(row):
    links = []
    for group in row["host_groups"]:
        link = "view.py?view_name=hostgroup&hostgroup=" + group
        if html.var("display_options"):
            link += "&display_options=%s" % html.attrencode(html.var("display_options"))
        links.append('<a href="%s">%s</a>' % (link, group))
    return "", ", ".join(links)

multisite_painters["host_group_memberlist"] = {
    "title"   : _("Host groups the host is member of"),
    "short"   : _("Groups"),
    "columns" : [ "host_groups" ],
    "groupby" : lambda row: tuple(row["host_groups"]),
    "paint"   : paint_host_group_memberlist,
}

multisite_painters["host_contacts"] = {
    "title"   : _("Host contacts"),
    "short"   : _("Contacts"),
    "columns" : ["host_contacts"],
    "paint"   : lambda row: (None, ", ".join(row["host_contacts"])),
}

multisite_painters["host_contact_groups"] = {
    "title"   : _("Host contact groups"),
    "short"   : _("Contact groups"),
    "columns" : ["host_contact_groups"],
    "paint"   : lambda row: (None, ", ".join(row["host_contact_groups"])),
}

multisite_painters["host_custom_notes"] = {
    "title"   : _("Custom host notes"),
    "short"   : _("Notes"),
    "columns" : [ "host_name", "host_address", "host_plugin_output" ],
    "paint"   : lambda row: paint_custom_notes("hosts", row),
}

multisite_painters["host_comments"] = {
    "title"   : _("Host comments"),
    "short"   : _("Comments"),
    "columns" : [ "host_comments_with_info" ],
    "paint"   : lambda row: paint_comments("host_", row),
}

multisite_painters["host_in_downtime"] = {
    "title"   : _("Host in downtime"),
    "short"   : _("Downtime"),
    "columns" : ["host_scheduled_downtime_depth"],
    "paint"   : lambda row: paint_nagiosflag(row, "host_scheduled_downtime_depth", True),
}

multisite_painters["host_acknowledged"] = {
    "title"   : _("Host problem acknowledged"),
    "short"   : _("Ack"),
    "columns" : ["host_acknowledged"],
    "paint"   : lambda row: paint_nagiosflag(row, "host_acknowledged", False),
}

multisite_painters["host_staleness"] = {
    "title"   : _("Host staleness value"),
    "short"   : _("Staleness"),
    "columns" : ["host_staleness"],
    "paint"   : lambda row: ('', '%0.2f' % row.get('host_staleness', 0)),
}

multisite_painters["host_is_stale"] = {
    "title"   : _("Host is stale"),
    "short"   : _("Stale"),
    "columns" : ["host_staleness"],
    "paint"   : paint_is_stale,
    "sorter"  : 'svc_staleness',
}

multisite_painters["host_servicelevel"] = {
    "title"   : _("Host service level"),
    "short"   : _("Service Level"),
    "columns" : [ "host_custom_variable_names", "host_custom_variable_values" ],
    "paint"   : lambda row: paint_custom_var('host', 'EC_SL', row,
                            config.mkeventd_service_levels),
    "sorter"  : 'servicelevel',
}

multisite_painters["host_custom_vars"] = {
    "title"   : _("Host custom variables"),
    "columns" : [ "host_custom_variables" ],
    "groupby" : lambda row: tuple(row["host_custom_variables"].items()),
    "paint"   : lambda row: paint_custom_vars('host', row, [ 'FILENAME', 'TAGS', 'ADDRESS_4', 'ADDRESS_6',
                                                             'ADDRESS_FAMILY', 'NODEIPS', 'NODEIPS_4', 'NODEIPS_6' ]),
}

def paint_discovery_output(field, row):
    value = row[field]
    if field == "discovery_state":
        ruleset_url   = "wato.py?mode=edit_ruleset&varname=ignored_services"
        discovery_url = "wato.py?mode=inventory&host=%s&mode=inventory" % row["host_name"]

        return None, {
            "ignored"     : html.render_icon_button(ruleset_url, 'Disabled (configured away by admin)', 'rulesets') + "Disabled (configured away by admin)",
            "vanished"    : html.render_icon_button(discovery_url, 'Vanished (checked, but no longer exist)', 'services') + "Vanished (checked, but no longer exist)",
            "unmonitored" : html.render_icon_button(discovery_url, 'Available (missing)', 'services') + "Available (missing)"
        }.get(value, value)
    elif field == "discovery_service" and row["discovery_state"] == "vanished":
        link = "view.py?view_name=service&site=%s&host=%s&service=%s" % (
                html.urlencode(row["site"]),
                html.urlencode(row["host_name"]),
                html.urlencode(value))
        return None, "<div><a href=\"%s\">%s</a></div>" % (link, value)
    else:
        return None, value

multisite_painters["service_discovery_state"] = {
    "title": _("Service discovery: State"),
    "short": _("State"),
    "columns": [ "discovery_state" ],
    "paint": lambda row: paint_discovery_output("discovery_state", row)
}

multisite_painters["service_discovery_check"] = {
    "title": _("Service discovery: Check type"),
    "short": _("Check type"),
    "columns": [ "discovery_state", "discovery_check", "discovery_service" ],
    "paint": lambda row: paint_discovery_output("discovery_check", row)
}

multisite_painters["service_discovery_service"] = {
    "title": _("Service discovery: Service description"),
    "short": _("Service description"),
    "columns": [ "discovery_state", "discovery_check", "discovery_service" ],
    "paint": lambda row: paint_discovery_output("discovery_service", row)
}


#    _   _           _
#   | | | | ___  ___| |_ __ _ _ __ ___  _   _ _ __  ___
#   | |_| |/ _ \/ __| __/ _` | '__/ _ \| | | | '_ \/ __|
#   |  _  | (_) \__ \ || (_| | | | (_) | |_| | |_) \__ \
#   |_| |_|\___/|___/\__\__, |_|  \___/ \__,_| .__/|___/
#                       |___/                |_|
#
def paint_hg_host_list(row):
    h = "<div class=objectlist>"
    for host, state, checked in row["hostgroup_members_with_state"]:
        link = "view.py?view_name=host&site=%s&host=%s" % (
                html.urlencode(row["site"]),
                html.urlencode(host))
        if checked:
            css = "hstate%d" % state
        else:
            css = "hstatep"
        h += "<div class=\"%s\"><a href=\"%s\">%s</a></div>" % (css, link, host)
    h += "</div>"
    return "", h

multisite_painters["hostgroup_hosts"] = {
    "title"   : _("Hosts colored according to state (Host Group)"),
    "short"   : _("Hosts"),
    "columns" : [ "hostgroup_members_with_state" ],
    "paint"   : paint_hg_host_list,
}

multisite_painters["hg_num_services"] = {
    "title"   : _("Number of services (Host Group)"),
    "short"   : "",
    "columns" : [ "hostgroup_num_services" ],
    "paint"   : lambda row: (None, str(row["hostgroup_num_services"])),
}

multisite_painters["hg_num_services_ok"] = {
    "title"   : _("Number of services in state OK (Host Group)"),
    "short"   : _("O"),
    "columns" : [ "hostgroup_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["hostgroup_num_services_ok"]),
}

multisite_painters["hg_num_services_warn"] = {
    "title"   : _("Number of services in state WARN (Host Group)"),
    "short"   : _("W"),
    "columns" : [ "hostgroup_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["hostgroup_num_services_warn"]),
}

multisite_painters["hg_num_services_crit"] = {
    "title"   : _("Number of services in state CRIT (Host Group)"),
    "short"   : _("C"),
    "columns" : [ "hostgroup_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["hostgroup_num_services_crit"]),
}

multisite_painters["hg_num_services_unknown"] = {
    "title"   : _("Number of services in state UNKNOWN (Host Group)"),
    "short"   : _("U"),
    "columns" : [ "hostgroup_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["hostgroup_num_services_unknown"]),
}

multisite_painters["hg_num_services_pending"] = {
    "title"   : _("Number of services in state PENDING (Host Group)"),
    "short"   : _("P"),
    "columns" : [ "hostgroup_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["hostgroup_num_services_pending"]),
}

multisite_painters["hg_num_hosts_up"] = {
    "title"   : _("Number of hosts in state UP (Host Group)"),
    "short"   : _("Up"),
    "columns" : [ "hostgroup_num_hosts_up" ],
    "paint"   : lambda row: paint_host_count(0, row["hostgroup_num_hosts_up"]),
}

multisite_painters["hg_num_hosts_down"] = {
    "title"   : _("Number of hosts in state DOWN (Host Group)"),
    "short"   : _("Dw"),
    "columns" : [ "hostgroup_num_hosts_down" ],
    "paint"   : lambda row: paint_host_count(1, row["hostgroup_num_hosts_down"]),
}

multisite_painters["hg_num_hosts_unreach"] = {
    "title"   : _("Number of hosts in state UNREACH (Host Group)"),
    "short"   : _("Un"),
    "columns" : [ "hostgroup_num_hosts_unreach" ],
    "paint"   : lambda row: paint_host_count(2, row["hostgroup_num_hosts_unreach"]),
}

multisite_painters["hg_num_hosts_pending"] = {
    "title"   : _("Number of hosts in state PENDING (Host Group)"),
    "short"   : _("Pd"),
    "columns" : [ "hostgroup_num_hosts_pending" ],
    "paint"   : lambda row: paint_host_count(None, row["hostgroup_num_hosts_pending"]),
}

multisite_painters["hg_name"] = {
    "title"   : _("Hostgroup name"),
    "short"   : _("Name"),
    "columns" : ["hostgroup_name"],
    "paint"   : lambda row: (None, row["hostgroup_name"]),
}

multisite_painters["hg_alias"] = {
    "title"   : _("Hostgroup alias"),
    "short"   : _("Alias"),
    "columns" : ["hostgroup_alias"],
    "paint"   : lambda row: (None, row["hostgroup_alias"]),
}

#    ____                  _
#   / ___|  ___ _ ____   _(_) ___ ___  __ _ _ __ ___  _   _ _ __  ___
#   \___ \ / _ \ '__\ \ / / |/ __/ _ \/ _` | '__/ _ \| | | | '_ \/ __|
#    ___) |  __/ |   \ V /| | (_|  __/ (_| | | | (_) | |_| | |_) \__ \
#   |____/ \___|_|    \_/ |_|\___\___|\__, |_|  \___/ \__,_| .__/|___/
#                                     |___/                |_|

multisite_painters["sg_services"] = {
    "title"   : _("Services colored according to state (Service Group)"),
    "short"   : _("Services"),
    "columns" : [ "servicegroup_members_with_state" ],
    "paint"   : lambda row: paint_service_list(row, "servicegroup_members_with_state"),
}

multisite_painters["sg_num_services"] = {
    "title"   : _("Number of services (Service Group)"),
    "short"   : "",
    "columns" : [ "servicegroup_num_services" ],
    "paint"   : lambda row: (None, str(row["servicegroup_num_services"])),
}

multisite_painters["sg_num_services_ok"] = {
    "title"   : _("Number of services in state OK (Service Group)"),
    "short"   : _("O"),
    "columns" : [ "servicegroup_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["servicegroup_num_services_ok"])
}

multisite_painters["sg_num_services_warn"] = {
    "title"   : _("Number of services in state WARN (Service Group)"),
    "short"   : _("W"),
    "columns" : [ "servicegroup_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["servicegroup_num_services_warn"])
}

multisite_painters["sg_num_services_crit"] = {
    "title"   : _("Number of services in state CRIT (Service Group)"),
    "short"   : _("C"),
    "columns" : [ "servicegroup_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["servicegroup_num_services_crit"])
}

multisite_painters["sg_num_services_unknown"] = {
    "title"   : _("Number of services in state UNKNOWN (Service Group)"),
    "short"   : _("U"),
    "columns" : [ "servicegroup_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["servicegroup_num_services_unknown"])
}

multisite_painters["sg_num_services_pending"] = {
    "title"   : _("Number of services in state PENDING (Service Group)"),
    "short"   : _("P"),
    "columns" : [ "servicegroup_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["servicegroup_num_services_pending"])
}
multisite_painters["sg_name"] = {
    "title" : _("Servicegroup name"),
    "short" : _("Name"),
    "columns" : ["servicegroup_name"],
    "paint" : lambda row: (None, row["servicegroup_name"])
}
multisite_painters["sg_alias"] = {
    "title" : _("Servicegroup alias"),
    "short" : _("Alias"),
    "columns" : ["servicegroup_alias"],
    "paint" : lambda row: (None, row["servicegroup_alias"])
}


multisite_painters["link_to_pnp_service"] = {
    "title"   : _("(obsolete) Link to PNP4Nagios"),
    "short"   : _("PNP"),
    "columns" : [ "site", "host_name", "service_description", "service_perf_data"],
    "paint"   : lambda row: ("", "")
}

#     ____                                     _
#    / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___
#   | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|
#   | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \
#    \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/
#

multisite_painters["comment_id"] = {
    "title"   : _("Comment id"),
    "short"   : _("ID"),
    "columns" : ["comment_id"],
    "paint"   : lambda row: (None, str(row["comment_id"])),
}
multisite_painters["comment_author"] = {
    "title"   : _("Comment author"),
    "short"   : _("Author"),
    "columns" : ["comment_author"],
    "paint"   : lambda row: (None, row["comment_author"]),
}

multisite_painters["comment_comment"] = {
    "title"   : _("Comment text"),
    "columns" : ["comment_comment"],
    "paint"   : lambda row: (None, format_plugin_output(row["comment_comment"])),
}

multisite_painters["comment_what"] = {
    "title"   : _("Comment type (host/service)"),
    "short"   : _("Type"),
    "columns" : ["comment_type"],
    "paint"   : lambda row: (None, row["comment_type"] == 1 and _("Host") or _("Service")),
}

multisite_painters["comment_time"] = {
    "title"   : _("Comment entry time"),
    "short"   : _("Time"),
    "columns" : ["comment_entry_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["comment_entry_time"], True, 3600),
}

multisite_painters["comment_expires"] = {
    "title"   : _("Comment expiry time"),
    "short"   : _("Expires"),
    "columns" : ["comment_expire_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["comment_expire_time"], row["comment_expire_time"] != 0, 3600, what='future'),
}

def paint_comment_entry_type(row):
    t = row["comment_entry_type"]
    linkview = None
    if t == 1:
        icon = "comment"
        help = _("Comment")
    elif t == 2:
        icon = "downtime"
        help = _("Downtime")
        if row["service_description"]:
            linkview = "downtimes_of_service"
        else:
            linkview = "downtimes_of_host"

    elif t == 3:
        icon = "flapping"
        help = _("Flapping")
    elif t == 4:
        icon = "ack"
        help = _("Acknowledgement")
    else:
        return "", ""
    code = html.render_icon(icon, help)
    if linkview:
        code = link_to_view(code, row, linkview)
    return "icons", code

multisite_painters["comment_entry_type"] = {
    "title"   : _("Comment entry type (user/downtime/flapping/ack)"),
    "short"   : _("E.Type"),
    "columns" : ["comment_entry_type", "host_name", "service_description" ],
    "paint"   : paint_comment_entry_type,
}

#    ____                      _   _
#   |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___
#   | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|
#   | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \
#   |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/
#


multisite_painters["downtime_id"] = {
    "title"   : _("Downtime id"),
    "short"   : _("ID"),
    "columns" : ["downtime_id"],
    "paint"   : lambda row: (None, row["downtime_id"]),
}

multisite_painters["downtime_author"] = {
    "title"   : _("Downtime author"),
    "short"   : _("Author"),
    "columns" : ["downtime_author"],
    "paint"   : lambda row: (None, row["downtime_author"]),
}

multisite_painters["downtime_comment"] = {
    "title"   : _("Downtime comment"),
    "short"   : _("Comment"),
    "columns" : ["downtime_comment"],
    "paint"   : lambda row: (None, format_plugin_output(row["downtime_comment"])),
}

multisite_painters["downtime_fixed"] = {
    "title"   : _("Downtime start mode"),
    "short"   : _("Mode"),
    "columns" : ["downtime_fixed"],
    "paint"   : lambda row: (None, row["downtime_fixed"] == 0 and _("flexible") or _("fixed")),
}

multisite_painters["downtime_origin"] = {
    "title"   : _("Downtime origin"),
    "short"   : _("Origin"),
    "columns" : ["downtime_origin"],
    "paint"   : lambda row: (None, row["downtime_origin"] == 1 and _("configuration") or _("command")),
}

def paint_downtime_recurring(row):
    try:
        wato.recurring_downtimes_types
    except:
        return "", _("(not supported)")

    r = row["downtime_recurring"]
    if not r:
        return "", _("no")
    else:
        return "", wato.recurring_downtimes_types.get(r, _("(unknown: %d)") % r)

multisite_painters["downtime_recurring"] = {
    "title"   : _("Downtime recurring interval"),
    "short"   : _("Recurring"),
    "columns" : ["downtime_recurring"],
    "paint"   : paint_downtime_recurring,
}

multisite_painters["downtime_what"] = {
    "title"   : _("Downtime for host/service"),
    "short"   : _("for"),
    "columns" : ["downtime_is_service"],
    "paint"   : lambda row: (None, row["downtime_is_service"] and _("Service") or _("Host")),
}

multisite_painters["downtime_type"] = {
    "title"   : _("Downtime active or pending"),
    "short"   : _("act/pend"),
    "columns" : ["downtime_type"],
    "paint"   : lambda row: (None, row["downtime_type"] == 0 and _("active") or _("pending")),
}

multisite_painters["downtime_entry_time"] = {
    "title"   : _("Downtime entry time"),
    "short"   : _("Entry"),
    "columns" : ["downtime_entry_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["downtime_entry_time"], True, 3600),
}

multisite_painters["downtime_start_time"] = {
    "title"   : _("Downtime start time"),
    "short"   : _("Start"),
    "columns" : ["downtime_start_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["downtime_start_time"], True, 3600, what="both"),
}

multisite_painters["downtime_end_time"] = {
    "title"   : _("Downtime end time"),
    "short"   : _("End"),
    "columns" : ["downtime_end_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["downtime_end_time"], True, 3600, what="both"),
}

def paint_downtime_duration(row):
    if row["downtime_fixed"] == 0:
        return "number", "%02d:%02d:00" % divmod(row["downtime_duration"] / 60, 60)
    else:
        return "", ""

multisite_painters["downtime_duration"] = {
    "title"   : _("Downtime duration (if flexible)"),
    "short"   : _("Flex. Duration"),
    "columns" : ["downtime_duration", "downtime_fixed"],
    "paint"   : paint_downtime_duration,
}

#    _
#   | |    ___   __ _
#   | |   / _ \ / _` |
#   | |__| (_) | (_| |
#   |_____\___/ \__, |
#               |___/

multisite_painters["log_message"] = {
    "title"   : _("Log: complete message"),
    "short"   : _("Message"),
    "columns" : ["log_message"],
    "paint"   : lambda row: ("", html.attrencode(row["log_message"])),
}

def paint_log_plugin_output(row):
    output = row["log_plugin_output"]
    comment = row["log_comment"]
    if output:
        return "", format_plugin_output(output, row)
    elif comment:
        return "", comment
    else:
        log_type = row["log_type"]
        lst = row["log_state_type"]
        if "FLAPPING" in log_type:
            if "HOST" in log_type:
                what = _("host")
            else:
                what = _("service")
            if lst == "STOPPED":
                return "", _("The %s stopped flapping") % what
            else:
                return "", _("The %s started flapping") % what

        elif lst:
            return "", (lst + " - " + log_type)
        else:
            return "", ""


multisite_painters["log_plugin_output"] = {
    "title"   : _("Log: Output"),
    "short"   : _("Output"),
    "columns" : ["log_plugin_output", "log_type", "log_state_type", "log_comment" ],
    "paint"   : paint_log_plugin_output,
}


def paint_log_type(row):
    lt = row["log_type"]
    if "HOST" in lt:
        return "", _("Host")
    elif "SERVICE" in lt or "SVC" in lt:
        return "", _("Service")
    else:
        return "", _("Program")


multisite_painters["log_what"] = {
    "title"   : _("Log: host or service"),
    "short"   : _("Host/Service"),
    "columns" : [ "log_type" ],
    "paint"   : paint_log_type,
}


multisite_painters["log_attempt"] = {
    "title"   : _("Log: number of check attempt"),
    "short"   : _("Att."),
    "columns" : ["log_attempt"],
    "paint"   : lambda row: ("", str(row["log_attempt"])),
}
multisite_painters["log_state_type"] = {
    "title"   : _("Log: type of state (hard/soft/stopped/started)"),
    "short"   : _("Type"),
    "columns" : ["log_state_type"],
    "paint"   : lambda row: ("", row["log_state_type"]),
}
multisite_painters["log_type"] = {
    "title"   : _("Log: event"),
    "short"   : _("Event"),
    "columns" : ["log_type"],
    "paint"   : lambda row: ("nowrap", row["log_type"]),
}
multisite_painters["log_contact_name"] = {
    "title"   : _("Log: contact name"),
    "short"   : _("Contact"),
    "columns" : ["log_contact_name"],
    "paint"   : lambda row: ("nowrap", row["log_contact_name"]),
}
multisite_painters["log_command"] = {
    "title"   : _("Log: command/plugin"),
    "short"   : _("Command"),
    "columns" : ["log_command_name"],
    "paint"   : lambda row: ("nowrap", row["log_command_name"]),
}


def paint_log_icon(row):
    img = None
    log_type = row["log_type"]
    log_state = row["log_state"]

    if log_type == "SERVICE ALERT":
        img = { 0: "ok", 1: "warn", 2:"crit", 3:"unknown" }.get(row["log_state"])
        title = _("Service Alert")

    elif log_type == "HOST ALERT":
        img = { 0: "up", 1: "down", 2:"unreach" }.get(row["log_state"])
        title = _("Host Alert")

    elif log_type.endswith("ALERT HANDLER STARTED"):
        img = "alert_handler_started"
        title = _("Alert Handler Started")

    elif log_type.endswith("ALERT HANDLER STOPPED"):
        if log_state == 0:
            img = "alert_handler_stopped"
            title = _("Alert handler Stopped")
        else:
            img = "alert_handler_failed"
            title = _("Alert handler failed")


    elif "DOWNTIME" in log_type:
        if row["log_state_type"] in [ "END", "STOPPED" ]:
            img = "downtimestop"
            title = _("Downtime stopped")
        else:
            img = "downtime"
            title = _("Downtime")

    elif log_type.endswith("NOTIFICATION"):
        if row["log_command_name"] == "check-mk-notify":
            img = "cmk_notify"
            title = _("Core produced a notification")
        else:
            img = "notify"
            title = _("User notification")

    elif log_type.endswith("NOTIFICATION RESULT"):
        img = "notify_result"
        title = _("Final notification result")

    elif log_type.endswith("NOTIFICATION PROGRESS"):
        img = "notify_progress"
        title = _("The notification is being processed")

    elif log_type == "EXTERNAL COMMAND":
        img = "command"
        title = _("External command")

    elif "restarting..." in log_type:
        img = "restart"
        title = _("Core restarted")

    elif "Reloading configuration" in log_type:
        img = "reload"
        title = _("Core configuration reloaded")

    elif "starting..." in log_type:
        img = "start"
        title = _("Core started")

    elif "shutdown..." in log_type or "shutting down" in log_type:
        img = "stop"
        title = _("Core stopped")

    elif " FLAPPING " in log_type:
        img = "flapping"
        title = _("Flapping")

    elif "ACKNOWLEDGE ALERT" in log_type:
        if row["log_state_type"] == "STARTED":
            img = "ack"
            title = _("Acknowledged")
        else:
            img = "ackstop"
            title = _("Stopped acknowledgement")

    if img:
        return "icon", html.render_icon("alert_"+img, help=title)
    else:
        return "icon", ""

multisite_painters["log_icon"] = {
    "title"   : _("Log: event icon"),
    "short"   : "",
    "columns" : ["log_type", "log_state", "log_state_type", "log_command_name"],
    "paint"   : paint_log_icon,
}

multisite_painters["log_options"] = {
    "title"   : _("Log: informational part of message"),
    "short"   : _("Info"),
    "columns" : ["log_options"],
    "paint"   : lambda row: ("", html.attrencode(row["log_options"])),
}

def paint_log_comment(msg):
    if ';' in msg:
        parts = msg.split(';')
        if len(parts) > 6:
          return ("", html.attrencode(parts[-1]))
    return ("", "")

multisite_painters["log_comment"] = {
    "title"   : _("Log: comment"),
    "short"   : _("Comment"),
    "columns" : ["log_options"],
    "paint"   : lambda row: paint_log_comment(row['log_options']),
}

multisite_painters["log_time"] = {
    "title"   : _("Log: entry time"),
    "short"   : _("Time"),
    "columns" : ["log_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["log_time"], True, 3600 * 24),
}

multisite_painters["log_lineno"] = {
    "title"   : _("Log: line number in log file"),
    "short"   : _("Line"),
    "columns" : ["log_lineno"],
    "paint"   : lambda row: ("number", str(row["log_lineno"])),
}

multisite_painters["log_date"] = {
    "title"   : _("Log: day of entry"),
    "short"   : _("Date"),
    "columns" : ["log_time"],
    "groupby" : lambda row: paint_day(row["log_time"])[1],
    "paint"   : lambda row: paint_day(row["log_time"]),
}

def paint_log_state(row):
    state = row["log_state"]

    # Notification result/progress lines don't hold real states. They hold notification plugin
    # exit results (0: ok, 1: temp issue, 2: perm issue). We display them as service states.
    if row["log_service_description"] \
       or row["log_type"].endswith("NOTIFICATION RESULT") \
       or row["log_type"].endswith("NOTIFICATION PROGRESS"):
        return paint_service_state_short({"service_has_been_checked":1, "service_state" : state})
    else:
        return paint_host_state_short({"host_has_been_checked":1, "host_state" : state})

multisite_painters["log_state"] = {
    "title"   : _("Log: state of host/service at log time"),
    "short"   : _("State"),
    "columns" : ["log_state", "log_state_type", "log_service_description", "log_type"],
    "paint"   : paint_log_state,
}

# Alert statistics

multisite_painters["alert_stats_ok"] = {
    "title"   : _("Alert Statistics: Number of recoveries"),
    "short"   : _("OK"),
    "columns" : [ "alerts_ok" ],
    "paint"   : lambda row: ("", str(row["alerts_ok"])),
}

multisite_painters["alert_stats_warn"] = {
    "title"   : _("Alert Statistics: Number of warnings"),
    "short"   : _("WARN"),
    "columns" : [ "alerts_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["alerts_warn"]),
}

multisite_painters["alert_stats_crit"] = {
    "title" : _("Alert Statistics: Number of critical alerts"),
    "short" : _("CRIT"),
    "columns" : [ "alerts_crit" ],
    "paint" : lambda row: paint_svc_count(2, row["alerts_crit"])
}

multisite_painters["alert_stats_unknown"] = {
    "title" : _("Alert Statistics: Number of unknown alerts"),
    "short" : _("UNKN"),
    "columns" : [ "alerts_unknown" ],
    "paint" : lambda row: paint_svc_count(3, row["alerts_unknown"])
}

multisite_painters["alert_stats_problem"] = {
    "title" : _("Alert Statistics: Number of problem alerts"),
    "short" : _("PROB"),
    "columns" : [ "alerts_problem" ],
    "paint" : lambda row: paint_svc_count('s', row["alerts_problem"])
}

#
# HOSTTAGS
#

def paint_host_tags(row):
    return "", get_host_tags(row)

multisite_painters["host_tags"] = {
    "title"   : _("Host tags (raw)"),
    "short"   : _("Tags"),
    "columns" : [ "host_custom_variable_names", "host_custom_variable_values" ],
    "paint"   : paint_host_tags,
    "sorter"  : 'host',
}

def paint_host_tags_with_titles(row):
    output = ''
    misc_tags = []
    for tag in get_host_tags(row).split():
        group_title = config.tag_group_title(tag)
        if group_title:
            output += group_title + ': ' + (config.tag_alias(tag) or tag) + '<br />\n'
        else:
            misc_tags.append(tag)

    if misc_tags:
        output += _('Misc:') + ' ' + ', '.join(misc_tags)

    return "", output

multisite_painters["host_tags_with_titles"] = {
    "title"   : _("Host tags (with titles)"),
    "short"   : _("Tags"),
    "columns" : [ "host_custom_variable_names", "host_custom_variable_values" ],
    "paint"   : paint_host_tags_with_titles,
    "sorter"  : 'host',
}


def paint_host_tag(row, tgid):
    tags_of_host = get_host_tags(row).split()

    for t in get_tag_group(tgid)[1]:
        if t[0] in tags_of_host:
            return "", t[1]
    return "", _("N/A")

# Use title of the tag value for grouping, not the complete
# dictionary of custom variables!
def groupby_host_tag(row, tgid):
    cssclass, title = paint_host_tag(row, tgid)
    return title

def load_host_tag_painters():
    # first remove all old painters to reflect delted painters during runtime
    for key in multisite_painters.keys():
        if key.startswith('host_tag_'):
            del multisite_painters[key]

    for entry in config.wato_host_tags:
        tgid = entry[0]
        tit  = entry[1]
        ch   = entry[2]

        long_tit = tit
        if '/' in tit:
            topic, tit = tit.split('/', 1)
            if topic:
                long_tit = topic + ' / ' + tit
            else:
                long_tit = tit

        multisite_painters["host_tag_" + tgid] = {
            "title"   : _("Host tag:") + ' ' + long_tit,
            "name"    : "host_tag_" + tgid,
            "short"   : tit,
            "columns" : [ "host_custom_variables" ],
            "paint"   : paint_host_tag,
            "groupby" : groupby_host_tag,
            "args"    : [ tgid ],
        }
