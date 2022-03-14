#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    ManualCheckParameterRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupEnforcedServicesApplications,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    FixedValue,
    Integer,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)


def _transform_inv_domino_tasks_rules(par):
    return (
        par
        if "default_params" in par
        else {
            "descr": par["descr"],
            "match": par["match"],
            "default_params": {
                "levels": par["levels"],
            },
        }
    )


def _vs_levels(help_txt):
    return Tuple(
        title=_("Levels on task count"),
        help=help_txt,
        elements=[
            Integer(
                title=_("Critical below"),
                unit=_("tasks"),
                default_value=1,
            ),
            Integer(
                title=_("Warning below"),
                unit=_("tasks"),
                default_value=1,
            ),
            Integer(
                title=_("Warning above"),
                unit=_("tasks"),
                default_value=99999,
            ),
            Integer(
                title=_("Critical above"),
                unit=_("tasks"),
                default_value=99999,
            ),
        ],
    )


def _valuespec_inv_domino_tasks_rules():
    return Transform(
        valuespec=Dictionary(
            title=_("Lotus Domino task discovery"),
            help=_(
                "This rule controls the discovery of tasks on Lotus Domino systems. "
                "Any changes later on require a host re-discovery"
            ),
            elements=[
                (
                    "descr",
                    TextInput(
                        title=_("Service Description"),
                        allow_empty=False,
                        help=_(
                            "<p>The service description may contain one or more occurances of <tt>%s</tt>. In this "
                            "case, the pattern must be a regular expression prefixed with ~. For each "
                            '<tt>%s</tt> in the description, the expression has to contain one "group". A group '
                            "is a subexpression enclosed in brackets, for example <tt>(.*)</tt> or "
                            "<tt>([a-zA-Z]+)</tt> or <tt>(...)</tt>. When the inventory finds a task "
                            "matching the pattern, it will substitute all such groups with the actual values when "
                            "creating the check. In this way one rule can create several checks on a host.</p>"
                            "<p>If the pattern contains more groups than occurrences of <tt>%s</tt> in the service "
                            "description, only the first matching subexpressions are used for the service "
                            "descriptions. The matched substrings corresponding to the remaining groups "
                            "are nevertheless copied into the regular expression.</p>"
                            "<p>As an alternative to <tt>%s</tt> you may also use <tt>%1</tt>, <tt>%2</tt>, etc. "
                            "These expressions will be replaced by the first, second, ... matching group, allowing "
                            "you to reorder things.</p>"
                        ),
                    ),
                ),
                (
                    "match",
                    Alternative(
                        title=_("Task Matching"),
                        elements=[
                            TextInput(
                                title=_("Exact name of the task"),
                                size=50,
                            ),
                            Transform(
                                valuespec=RegExp(
                                    size=50,
                                    mode=RegExp.prefix,
                                ),
                                title=_("Regular expression matching command line"),
                                help=_("This regex must match the <i>beginning</i> of the task"),
                                forth=lambda x: x[1:],  # remove ~
                                back=lambda x: "~" + x,  # prefix ~
                            ),
                            FixedValue(
                                value=None,
                                totext="",
                                title=_("Match all tasks"),
                            ),
                        ],
                        match=lambda x: (not x and 2) or (x[0] == "~" and 1 or 0),
                        default_value="foo",
                    ),
                ),
                (
                    "default_params",
                    Dictionary(
                        title=_("Check parameters"),
                        elements=[
                            (
                                "levels",
                                _vs_levels(
                                    _(
                                        "Please note that if you specify and also if you modify "
                                        "levels here, the change is activated only during an "
                                        "inventory. Saving this rule is not enough. This is due to "
                                        "the nature of inventory rules."
                                    )
                                ),
                            ),
                        ],
                        optional_keys=False,
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=_transform_inv_domino_tasks_rules,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="all",
        name="inv_domino_tasks_rules",
        valuespec=_valuespec_inv_domino_tasks_rules,
    )
)


def _item_spec_domino_tasks():
    return TextInput(
        title=_("Name of service"),
        help=_("This name will be used in the description of the service"),
        allow_empty=False,
        regex="^[a-zA-Z_0-9 _.-]*$",
        regex_error=_(
            "Please use only a-z, A-Z, 0-9, space, underscore, "
            "dot and hyphen for your service description"
        ),
    )


def _transform_valuespec_domino_tasks(par):
    if "levels" not in par:
        par["levels"] = (
            par.pop("warnmin"),
            par.pop("okmin"),
            par.pop("okmax"),
            par.pop("warnmax"),
        )
    return par


def _parameter_valuespec_domino_tasks():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "process",
                    Alternative(
                        title=_("Name of the task"),
                        elements=[
                            TextInput(
                                title=_("Exact name of the task"),
                                size=50,
                            ),
                            Transform(
                                valuespec=RegExp(
                                    size=50,
                                    mode=RegExp.prefix,
                                ),
                                title=_("Regular expression matching tasks"),
                                help=_(
                                    "This regex must match the <i>beginning</i> of the complete "
                                    "command line of the task including arguments"
                                ),
                                forth=lambda x: x[1:],  # remove ~
                                back=lambda x: "~" + x,  # prefix ~
                            ),
                            FixedValue(
                                value=None,
                                totext="",
                                title=_("Match all tasks"),
                            ),
                        ],
                        match=lambda x: (not x and 2) or (x[0] == "~" and 1 or 0),
                    ),
                ),
                (
                    "levels",
                    _vs_levels(
                        _("Specify levels on the minimum and maximum number of tasks."),
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=_transform_valuespec_domino_tasks,
    )


rulespec_registry.register(
    ManualCheckParameterRulespec(
        check_group_name="domino_tasks",
        group=RulespecGroupEnforcedServicesApplications,
        item_spec=_item_spec_domino_tasks,
        parameter_valuespec=_parameter_valuespec_domino_tasks,
        title=lambda: _("Lotus Domino Tasks"),
    )
)
