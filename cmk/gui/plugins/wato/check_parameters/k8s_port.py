#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Integer,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _item_spec_k8s_port():
    return TextAscii(
        title=_("Port"),
        help=_("Name or number of the port"),
    )


def _parameter_valuespec_k8s_port():
    return Dictionary(elements=[
        ('port', Integer(
            title=_('Port'),
            minvalue=0,
            maxvalue=65535,
        )),
        ('target_port', Integer(
            title=_('Target port'),
            minvalue=0,
            maxvalue=65535,
        )),
        ('node_port', Integer(
            title=_('Node port'),
            minvalue=0,
            maxvalue=65535,
        )),
        ('protocol',
         DropdownChoice(
             title=_('Protocol'),
             choices=[
                 ('TCP', _('TCP')),
                 ('UDP', _('UDP')),
                 ('HTTP', _('HTTP')),
                 ('PROXY', _('PROXY')),
                 ('SCTP', _('SCTP')),
             ],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="k8s_port",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_k8s_port,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_k8s_port,
        title=lambda: _("Kubernetes Port"),
    ))
