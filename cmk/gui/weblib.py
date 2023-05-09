#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

import cmk.gui.config as config
import cmk.gui.utils as utils
import cmk.gui.pages
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.exceptions import MKUserError


@cmk.gui.pages.register("tree_openclose")
def ajax_tree_openclose() -> None:
    tree = html.request.get_str_input_mandatory("tree")
    name = html.request.get_unicode_input_mandatory("name")

    config.user.set_tree_state(tree, name, html.request.get_str_input("state"))
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


def init_selection() -> None:
    """Generate the initial selection_id"""
    selection_id()
    config.user.cleanup_old_selections()


def selection_id() -> str:
    """Generates a selection id or uses the given one"""
    if not html.request.has_var('selection'):
        sel_id = utils.gen_id()
        html.request.set_var('selection', sel_id)
        return sel_id

    sel_id = html.request.get_str_input_mandatory('selection')

    # Avoid illegal file access by introducing .. or /
    if not re.match("^[-0-9a-zA-Z]+$", sel_id):
        new_id = utils.gen_id()
        html.request.set_var('selection', new_id)
        return new_id
    return sel_id


@cmk.gui.pages.register("ajax_set_rowselection")
def ajax_set_rowselection() -> None:
    ident = html.request.get_str_input_mandatory('id')
    action = html.request.get_str_input_mandatory('action', 'set')
    if action not in ['add', 'del', 'set', 'unset']:
        raise MKUserError(None, _('Invalid action'))

    rows = html.request.get_str_input_mandatory('rows', '').split(',')
    config.user.set_rowselection(selection_id(), ident, rows, action)
