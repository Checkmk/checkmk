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

import traceback

import six

import cmk.regex

import cmk.gui.config as config
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML

from cmk.plugin_loader import load_plugins

#.
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   '----------------------------------------------------------------------'

# Deprecated in 1.2.7i1
multisite_icons = []
# Use this structure for new icons
multisite_icons_and_actions = {}


def get_multisite_icons():
    icons = {}

    for icon_id, icon_config in multisite_icons_and_actions.items():
        icon = {
            "toplevel": False,
            "sort_index": 30,
        }
        icon.update(icon_config)
        icons[icon_id] = icon

    # multisite_icons has been deprecated, but to be compatible to old icon
    # plugins transform them to the new structure. We use part of the paint
    # function name as icon id.
    for icon_config in multisite_icons:
        icon = {
            "toplevel": False,
            "sort_index": 30,
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


def get_icons(what, row, toplevel):
    host_custom_vars = dict(
        zip(
            row["host_custom_variable_names"],
            row["host_custom_variable_values"],
        ))

    if what != 'host':
        custom_vars = dict(
            zip(
                row[what + "_custom_variable_names"],
                row[what + "_custom_variable_values"],
            ))
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
    icons = _process_multisite_icons(what, row, tags, host_custom_vars, toplevel)
    icons += _process_custom_user_icons_and_actions(user_action_ids, toplevel)
    return sorted(icons, key=lambda i: i[0])


def _process_multisite_icons(what, row, tags, custom_vars, toplevel):
    icons = []
    for icon_id, icon in get_multisite_icons().items():
        if icon.get('type', 'icon') == 'icon':
            try:
                title = None
                url = None
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
                except Exception:
                    if config.debug:
                        raise
                    result = ("alert",
                              "Exception in icon '%s': %s" % (icon_id, traceback.format_exc()))

                if result is None:
                    continue

                elif isinstance(result, six.string_types + (HTML,)):

                    # TODO: This is handling the deprecated API with 1.2.7. Remove this one day.
                    if result[0] == '<':
                        # seems like an old format icon (html code). In regular rendering
                        # case (html), it can simply be appended to the output. Otherwise
                        # extract the icon name from icon images
                        if html.output_format == "html":
                            icons.append((sort_index, result))
                        else:
                            # Strip icon names out of HTML code that is generated by htmllib.render_icon()
                            for n in cmk.regex.regex('<img src="([^"]*)"[^>]*>').findall(
                                    "%s" % result):
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

            except Exception:
                icons.append((sort_index,
                              'Exception in icon plugin!<br />' + traceback.format_exc()))
    return icons


def _process_custom_user_icons_and_actions(user_action_ids, toplevel):
    icons = []
    for uid in user_action_ids:
        try:
            icon = config.user_icons_and_actions[uid]
        except KeyError:
            continue  # Silently skip not existing icons

        if icon.get('toplevel', False) == toplevel:
            sort_index = icon.get('sort_index', 15)
            icons.append((sort_index, icon['icon'], icon.get('title'), icon.get('url')))

    return icons


# toplevel may be
#  True to get only columns for top level icons
#  False to get only columns for dropdown menu icons
#  None to get columns for all active icons
def iconpainter_columns(what, toplevel):
    cols = set([
        'site',
        'host_name',
        'host_address',
        'host_custom_variable_names',
        'host_custom_variable_values',
    ])

    if what == 'service':
        cols.update([
            'service_description',
            'service_custom_variable_names',
            'service_custom_variable_values',
        ])

    for icon in get_multisite_icons().itervalues():
        if toplevel is None or toplevel == icon['toplevel']:
            if 'columns' in icon:
                cols.update([what + '_' + c for c in icon['columns']])
            cols.update(["host_" + c for c in icon.get("host_columns", [])])
            if what == "service":
                cols.update(["service_" + c for c in icon.get("service_columns", [])])

    return cols


#.
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'

load_plugins(__file__, __package__)
