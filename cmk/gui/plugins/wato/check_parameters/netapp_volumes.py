#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.filesystem_utils import (
    fs_inodes_elements,
    fs_magic_elements,
    get_free_used_dynamic_valuespec,
    match_dual_level_type,
    size_trend_elements,
    transform_filesystem_free,
    transform_trend_mb_to_trend_bytes,
)
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Alternative, Dictionary, ListChoice, TextInput, Transform


def _parameter_valuespec_netapp_volumes():
    return Transform(
        valuespec=Dictionary(
            ignored_keys=["patterns"],
            elements=[
                (
                    "levels",
                    Alternative(
                        title=_("Levels for volume"),
                        show_alternative_title=True,
                        default_value=(80.0, 90.0),
                        match=match_dual_level_type,
                        elements=[
                            get_free_used_dynamic_valuespec("used", "volume", maxvalue=None),
                            Transform(
                                valuespec=get_free_used_dynamic_valuespec(
                                    "free", "volume", default_value=(20.0, 10.0)
                                ),
                                forth=transform_filesystem_free,
                                back=transform_filesystem_free,
                            ),
                        ],
                    ),
                ),
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
            ]
            + fs_magic_elements
            + fs_inodes_elements
            + size_trend_elements,
        ),
        forth=transform_trend_mb_to_trend_bytes,
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
