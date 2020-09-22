#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    TextAscii,
    Transform,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.check_parameters.mailqueue_length import mailqueue_params


def _parameter_valuespec_mail_queue_length():
    return Transform(
        mailqueue_params,
        forth=lambda old: not isinstance(old, dict) and {"deferred": old} or old,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mail_queue_length",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Mail queue name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mail_queue_length,
        title=lambda: _("Mails in outgoing mail queue"),
    ))
