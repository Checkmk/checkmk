#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, Filesize, Integer, Tuple


def _item_spec_docker_node_disk_usage():
    return DropdownChoice(
        title=_("Type"),
        help=_("Either Containers, Images, Local Volumes or Build Cache"),
        choices=[
            ("buildcache", _("Build Cache")),
            ("containers", _("Containers")),
            ("images", _("Images")),
            ("volumes", _("Local Volumes")),
        ],
    )


def _parameter_valuespec_docker_node_disk_usage():
    return Dictionary(
        help=_(
            "Allows to define levels for the counts and size of Docker Containers, Images, Local Volumes, and the Build Cache."
        ),
        elements=[
            (
                "size",
                Tuple(
                    title=_("Size"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "reclaimable",
                Tuple(
                    title=_("Reclaimable"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "count",
                Tuple(
                    title=_("Total count"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "active",
                Tuple(
                    title=_("Active"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="docker_node_disk_usage",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_docker_node_disk_usage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_docker_node_disk_usage,
        title=lambda: _("Docker node disk usage"),
    )
)
