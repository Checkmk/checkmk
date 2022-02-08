#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Filesize, Tuple

MEMORY_DEFAULT = 1024**3


def _memory_tuple(title):
    return Tuple(
        title=title,
        elements=[
            Filesize(title=_("Warning at"), default_value=MEMORY_DEFAULT),
            Filesize(title=_("Critical at"), default_value=MEMORY_DEFAULT),
        ],
    )


def _parameter_valuespec_esx_host_memory():
    return Dictionary(
        elements=[
            ("host", _memory_tuple(_("Host memory usage"))),
            ("guest", _memory_tuple(_("Guest memory usage"))),
            ("ballooned", _memory_tuple(_("Ballooned memory usage"))),
            ("private", _memory_tuple(_("Private memory usage"))),
            ("shared", _memory_tuple(_("Shared memory usage"))),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="esx_vsphere_vm_memory",
        group=RulespecGroupCheckParametersOperatingSystem,
        parameter_valuespec=_parameter_valuespec_esx_host_memory,
        title=lambda: _("ESX VM memory usage"),
    )
)
