#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    ListOfStrings,
    TextAscii,
    TextUnicode,
    Transform,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)


def _parameter_valuespec_fs_mount_options():
    expected = ListOfStrings(
        title=_("Expected mount options"),
        help=_("Specify all expected mount options here. If the list of "
               "actually found options differs from this list, the check will go "
               "warning or critical. Just the option <tt>commit</tt> is being "
               "ignored since it is modified by the power saving algorithms."),
        valuespec=TextUnicode(),
    )
    ignore = ListOfStrings(
        title=_("Mount options to ignore"),
        help=_("Specify all mount options that should be ignored when inspecting "
               "the list of actually found options. The options <tt>commit</tt>, "
               "<tt>localalloc</tt>, <tt>subvol</tt>, <tt>subvolid</tt> are "
               "ignored by default."),
        valuespec=TextUnicode(),
        default_value = ["commit=", "localalloc=", "subvol=", "subvolid="],
    )

    # The old parameterset was just a list of strings. We moved that list into a
    # dictionary with the key 'expected'.
    return Transform(
        Dictionary(
            title=_("Mount options"),
            elements=[
                ('expected', expected),
                ('ignore', ignore),
            ],
        ),
        forth = lambda params: params if isinstance(params, dict) else {'expected': params},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fs_mount_options",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("Mount point"), allow_empty=False),
        parameter_valuespec=_parameter_valuespec_fs_mount_options,
        title=lambda: _("Filesystem mount options (Linux/UNIX)"),
    ))
