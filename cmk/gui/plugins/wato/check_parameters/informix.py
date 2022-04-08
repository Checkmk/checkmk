#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Percentage, TextInput, Tuple


def _parameter_valuespec_informix_dbspaces():
    return Dictionary(elements=[
        (
            "levels",
            Tuple(
                title=_("Upper levels for the DB space size"),
                elements=[
                    Integer(title=_("Warning at")),
                    Integer(title=_("Critical at")),
                ],
            ),
        ),
        (
            "levels_perc",
            Tuple(
                title=_("Upper percentual levels for the DB space size"),
                elements=[
                    Percentage(title=_("Warning at"), default_value=80.0),
                    Percentage(title=_("Critical at"), default_value=85.0),
                ],
            ),
        ),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="informix_dbspaces",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_informix_dbspaces,
        title=lambda: _("Informix DB spaces"),
        item_spec=lambda: TextInput(title=_("The instance name")),
    ))


def _parameter_valuespec_informix_locks():
    return Dictionary(elements=[
        (
            "levels",
            Tuple(
                title=_("Upper levels for the number of locks"),
                elements=[
                    Integer(title=_("Warning at"), default_value=70),
                    Integer(title=_("Critical at"), default_value=80),
                ],
            ),
        ),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="informix_locks",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_informix_locks,
        title=lambda: _("Informix locks"),
        item_spec=lambda: TextInput(title=_("The instance name")),
    ))


def _parameter_valuespec_informix_logusage():
    return Dictionary(elements=[
        (
            "levels",
            Tuple(
                title=_("Upper levels for the logs usage size"),
                elements=[
                    Integer(title=_("Warning at")),
                    Integer(title=_("Critical at")),
                ],
            ),
        ),
        (
            "levels_perc",
            Tuple(
                title=_("Upper percentual levels for the logs usage size"),
                elements=[
                    Percentage(title=_("Warning at"), default_value=80.0),
                    Percentage(title=_("Critical at"), default_value=85.0),
                ],
            ),
        ),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="informix_logusage",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_informix_logusage,
        title=lambda: _("Informix log usage"),
        item_spec=lambda: TextInput(title=_("The instance name")),
    ))


def _parameter_valuespec_informix_sessions():
    return Dictionary(elements=[
        (
            "levels",
            Tuple(
                title=_("Upper levels for the number of sessions"),
                elements=[
                    Integer(title=_("Warning at"), default_value=50),
                    Integer(title=_("Critical at"), default_value=60),
                ],
            ),
        ),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="informix_sessions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_informix_sessions,
        title=lambda: _("Informix sessions"),
        item_spec=lambda: TextInput(title=_("The instance name")),
    ))


def _parameter_valuespec_informix_tabextents():
    return Dictionary(elements=[
        (
            "levels",
            Tuple(
                title=_("Upper levels for the number of table extents"),
                elements=[
                    Integer(title=_("Warning at"), default_value=40),
                    Integer(title=_("Critical at"), default_value=70),
                ],
            ),
        ),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="informix_tabextents",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_informix_tabextents,
        title=lambda: _("Informix table extents"),
        item_spec=lambda: TextInput(title=_("The instance name")),
    ))
