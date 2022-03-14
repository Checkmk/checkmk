#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Age, Dictionary, DropdownChoice, ListOf, TextInput, Tuple


def _item_spec_inotify():
    return TextInput(
        title=_("The filesystem path, prefixed with <i>File </i> or <i>Folder </i>"),
    )


def _parameter_valuespec_inotify():
    return Dictionary(
        help=_(
            "This rule allows you to set levels for specific Inotify changes. "
            "Keep in mind that you can only monitor operations which are actually "
            "enabled in the Inotify plugin. So it might be a good idea to cross check "
            "these levels here with the configuration rule in the agent bakery. "
        ),
        elements=[
            (
                "age_last_operation",
                ListOf(
                    valuespec=Tuple(
                        elements=[
                            DropdownChoice(
                                title=_("INotify Operation"),
                                choices=[
                                    ("create", _("Create")),
                                    ("delete", _("Delete")),
                                    ("open", _("Open")),
                                    ("modify", _("Modify")),
                                    ("access", _("Access")),
                                    ("movedfrom", _("Moved from")),
                                    ("movedto", _("Moved to")),
                                    ("moveself", _("Move self")),
                                ],
                            ),
                            Age(title=_("Warning at")),
                            Age(title=_("Critical at")),
                        ],
                    ),
                    title=_("Age of last operation"),
                    movable=False,
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="inotify",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_inotify,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_inotify,
        title=lambda: _("INotify Levels"),
    )
)
