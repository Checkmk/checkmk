#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | copyright mathias kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# this file is part of check_mk.
# the official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  gnu general public license  as published by
# the free software foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but without any warranty;  with-
# out even the implied warranty of  merchantability  or  fitness for a
# particular purpose. see the  gnu general public license for more de-
# tails. you should have  received  a copy of the  gnu  general public
# license along with gnu make; see the file  copying.  if  not,  write
# to the free software foundation, inc., 51 franklin st,  fifth floor,
# boston, ma 02110-1301 usa.

import re

import cmk.gui.config as config
import cmk.gui.utils as utils
import cmk.gui.pages
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.exceptions import MKUserError


@cmk.gui.pages.register("tree_openclose")
def ajax_tree_openclose():
    tree = html.request.var("tree")
    name = html.get_unicode_input("name")

    if not tree or not name:
        raise MKUserError(None, _('tree or name parameter missing'))

    config.user.set_tree_state(tree, name, html.request.var("state"))
    config.user.save_tree_states()
    html.write('OK')  # Write out something to make debugging easier


#   .--Row Selector--------------------------------------------------------.
#   |      ____                 ____       _           _                   |
#   |     |  _ \ _____      __ / ___|  ___| | ___  ___| |_ ___  _ __       |
#   |     | |_) / _ \ \ /\ / / \___ \ / _ \ |/ _ \/ __| __/ _ \| '__|      |
#   |     |  _ < (_) \ V  V /   ___) |  __/ |  __/ (__| || (_) | |         |
#   |     |_| \_\___/ \_/\_/   |____/ \___|_|\___|\___|\__\___/|_|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Saves and loads selected row information of the current user         |
#   +----------------------------------------------------------------------+


def init_selection():
    # Generate the initial selection_id
    selection_id()
    config.user.cleanup_old_selections()


# Generates a selection id or uses the given one
def selection_id():
    if not html.request.has_var('selection'):
        sel_id = utils.gen_id()
        html.request.set_var('selection', sel_id)
        return sel_id

    sel_id = html.request.var('selection')
    # Avoid illegal file access by introducing .. or /
    if not re.match("^[-0-9a-zA-Z]+$", sel_id):
        new_id = utils.gen_id()
        html.request.set_var('selection', new_id)
        return new_id
    return sel_id


@cmk.gui.pages.register("ajax_set_rowselection")
def ajax_set_rowselection():
    ident = html.request.var('id')

    action = html.request.var('action', 'set')
    if action not in ['add', 'del', 'set', 'unset']:
        raise MKUserError(None, _('Invalid action'))

    rows = html.request.var('rows', '').split(',')

    config.user.set_rowselection(selection_id(), ident, rows, action)
