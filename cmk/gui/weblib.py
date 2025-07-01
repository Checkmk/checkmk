#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.utils.selection_id import SelectionId


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("tree_openclose", ajax_tree_openclose))
    page_registry.register(PageEndpoint("ajax_set_rowselection", ajax_set_rowselection))


def ajax_tree_openclose(config: Config) -> None:
    tree = request.get_str_input_mandatory("tree")
    name = request.get_str_input_mandatory("name")

    user.set_tree_state(tree, name, request.get_str_input("state"))  # type: ignore[no-untyped-call]
    user.save_tree_states()
    response.set_data("OK")  # Write out something to make debugging easier


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
    user.cleanup_old_selections()


def ajax_set_rowselection(config: Config) -> None:
    ident = request.get_str_input_mandatory("id")
    action = request.get_str_input_mandatory("action", "set")
    if action not in ["add", "del", "set", "unset"]:
        raise MKUserError(None, _("Invalid action"))

    rows = request.get_str_input_mandatory("rows", "").split(",")
    user.set_rowselection(SelectionId.from_request(request), ident, rows, action)
