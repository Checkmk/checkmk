#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)

from cmk.gui.plugins.wato.check_parameters.utils import (
    fs_levels_elements,
    fs_magic_elements,
    size_trend_elements,
)


def _item_spec_network_fs():
    return TextAscii(title=_("Name of the mount point"),
                     help=_("For NFS enter the name of the mount point."))


def _parameter_valuespec_network_fs():
    return Dictionary(elements=(fs_levels_elements + fs_magic_elements + size_trend_elements + [
        (
            "has_perfdata",
            DropdownChoice(title=_("Performance data settings"),
                           choices=[
                               (True, _("Enable performance data")),
                               (False, _("Disable performance data")),
                           ],
                           default_value=False),
        ),
    ]),)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="network_fs",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_network_fs,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_network_fs,
        title=lambda: _("Network filesystem - overall status and usage (e.g. NFS)"),
    ))
