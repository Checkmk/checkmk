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

import cmk.utils.regex

import cmk.gui.config as config
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML

from cmk.utils.plugin_loader import load_plugins

from cmk.gui.plugins.views.icons.utils import (
    Icon,
    icon_and_action_registry,
)

#.
#   .--Plugin API----------------------------------------------------------.
#   |           ____  _             _            _    ____ ___             |
#   |          |  _ \| |_   _  __ _(_)_ __      / \  |  _ \_ _|            |
#   |          | |_) | | | | |/ _` | | '_ \    / _ \ | |_) | |             |
#   |          |  __/| | |_| | (_| | | | | |  / ___ \|  __/| |             |
#   |          |_|   |_|\__,_|\__, |_|_| |_| /_/   \_\_|  |___|            |
#   |                         |___/                                        |
#   '----------------------------------------------------------------------'

# Use this structure for new icons
# TODO: Move this to cmk.gui.views once this is only used by legacy view/icon plugins
multisite_icons_and_actions = {}


def get_multisite_icons():
    icons = {}

    for icon_class in icon_and_action_registry.values():
        icons[icon_class.ident()] = icon_class()

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
    user_icon_ids = custom_vars.get('ACTIONS', '').split(',')

    # Icons is a list of triple or quintuplets with these elements:
    # (toplevel, sort_index, html_code)
    #  -> TODO: can be removed one day, handles deprecated icon API
    #  -> this can only happen for toplevel_icons and when output
    #     is written to HTML
    #  -> or when an exception occured
    # (toplevel, sort_index, icon_name, title, url)
    icons = _process_icons(what, row, tags, host_custom_vars, toplevel, user_icon_ids)
    return sorted(icons, key=lambda i: i[0])


def _process_icons(what, row, tags, custom_vars, toplevel, user_icon_ids):
    icons = []
    for icon_id, icon in get_multisite_icons().items():
        if icon.toplevel() != toplevel:
            continue

        if icon.type() == "custom_icon" and icon_id not in user_icon_ids:
            continue

        if not config.user.may("icons_and_actions.%s" % icon_id):
            continue

        try:
            for result in _process_icon(what, row, tags, custom_vars, icon_id, icon):
                icons.append(result)
        except Exception:
            icons.append(
                (icon.sort_index(), 'Exception in icon plugin!<br />' + traceback.format_exc()))
    return icons


def _process_icon(what, row, tags, custom_vars, icon_id, icon):
    # In old versions, the icons produced html code directly. The new API
    # is that the icon functions need to return:
    # a) None          - nothing to be rendered
    # b) single string - the icon name (without .png)
    # c) tuple         - icon, title
    # d) triple        - icon, title, url
    try:
        result = icon.render(what, row, tags, custom_vars)
    except Exception:
        if config.debug:
            raise
        result = ("alert", "Exception in icon '%s': %s" % (icon_id, traceback.format_exc()))

    if result is None:
        return

    title, url = None, None
    if isinstance(result, six.string_types + (HTML,)):
        # TODO: This is handling the deprecated API with 1.2.7. Remove this one day. But there
        # are icons that still use this API. These need to be cleaned up before.
        # LM: There are icons that still use this API
        if result[0] == '<':
            # seems like an old format icon (html code). In regular rendering
            # case (html), it can simply be appended to the output. Otherwise
            # extract the icon name from icon images
            if html.output_format == "html":
                yield icon.sort_index(), result
            else:
                # Strip icon names out of HTML code that is generated by htmllib.render_icon()
                for n in cmk.utils.regex.regex('<img src="([^"]*)"[^>]*>').findall("%s" % result):
                    if n.startswith("images/"):
                        n = n[7:]
                    if n.startswith("icon_"):
                        n = n[5:]
                    if n.endswith(".png"):
                        n = n[:-4]
                    yield icon.sort_index(), n.encode('utf-8'), None, None
            return

        icon_name = result
    else:
        if len(result) == 2:
            icon_name, title = result
        elif len(result) == 3:
            icon_name, title, url = result

    yield icon.sort_index(), icon_name, title, url


# toplevel may be
#  True to get only columns for top level icons
#  False to get only columns for dropdown menu icons
#  None to get columns for all active icons
def iconpainter_columns(what, toplevel):
    cols = {
        'site',
        'host_name',
        'host_address',
        'host_custom_variable_names',
        'host_custom_variable_values',
    }

    if what == 'service':
        cols.update([
            'service_description',
            'service_custom_variable_names',
            'service_custom_variable_values',
        ])

    for icon in get_multisite_icons().itervalues():
        if toplevel is None or toplevel == icon.toplevel():
            cols.update([what + '_' + c for c in icon.columns()])
            cols.update(["host_" + c for c in icon.host_columns()])
            if what == "service":
                cols.update(["service_" + c for c in icon.service_columns()])

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
