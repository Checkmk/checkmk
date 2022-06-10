#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import FilesystemElements, vs_filesystem
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import ListChoice, TextInput


def _parameter_valuespec_netapp_volumes():
    return vs_filesystem(
        elements=[
            FilesystemElements.levels_unbound,
            FilesystemElements.magic_factor,
            FilesystemElements.inodes,
            FilesystemElements.size_trend,
        ],
        extra_elements=[
            (
                "perfdata",
                ListChoice(
                    title=_("Performance data for protocols"),
                    help=_("Specify for which protocol performance data should get recorded."),
                    choices=[
                        ("", _("Summarized data of all protocols")),
                        ("nfs", _("NFS")),
                        ("cifs", _("CIFS")),
                        ("san", _("SAN")),
                        ("fcp", _("FCP")),
                        ("iscsi", _("iSCSI")),
                    ],
                ),
            ),
        ],
        ignored_keys=["patterns"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netapp_volumes",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Volume name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netapp_volumes,
        title=lambda: _("NetApp Volumes"),
    )
)
