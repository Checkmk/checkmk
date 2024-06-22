#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui import bi
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    HTTPUrl,
    ListOf,
    Migrate,
    MonitoringState,
    RegExp,
    TextInput,
    Tuple,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword, RulespecGroupDatasourceProgramsApps
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


class MultisiteBiDatasource:
    def get_valuespec(self):
        return Dictionary(
            elements=self._get_dynamic_valuespec_elements(),
            optional_keys=["filter", "options", "assignments"],
        )

    def _get_dynamic_valuespec_elements(self):
        return [
            (
                "site",
                CascadingDropdown(
                    choices=[
                        ("local", _("Connect to the local site")),
                        (
                            "url",
                            _("Connect to site url"),
                            HTTPUrl(
                                help=_(
                                    "URL of the remote site, for example https://10.3.1.2/testsite"
                                )
                            ),
                        ),
                    ],
                    sorted=False,
                    orientation="horizontal",
                    title=_("Site connection"),
                ),
            ),
            (
                "credentials",
                CascadingDropdown(
                    choices=[
                        ("automation", _("Use the credentials of the 'automation' user")),
                        (
                            "configured",
                            _("Use the following credentials"),
                            Tuple(
                                elements=[
                                    TextInput(
                                        title=_("Automation user name"),
                                        allow_empty=True,
                                    ),
                                    MigrateToIndividualOrStoredPassword(
                                        title=_("Automation Secret"),
                                        allow_empty=True,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    help=_(
                        "Here you can configured the credentials to be used. Keep in mind that the <tt>automation</tt> user need "
                        "to exist if you choose this option"
                    ),
                    title=_("Login credentials"),
                    default_value="automation",
                ),
            ),
            ("filter", self._vs_filters()),
            ("assignments", self._vs_aggregation_assignments()),
            ("options", self._vs_options()),
        ]

    def _vs_aggregation_assignments(self):
        return Dictionary(
            title=_("Aggregation assignment"),
            elements=[
                (
                    "querying_host",
                    FixedValue(
                        value="querying_host", totext="", title=_("Assign to the querying host")
                    ),
                ),
                (
                    "affected_hosts",
                    FixedValue(
                        value="affected_hosts", totext="", title=_("Assign to the affected hosts")
                    ),
                ),
                (
                    "regex",
                    ListOf(
                        valuespec=Tuple(
                            orientation="horizontal",
                            elements=[
                                RegExp(
                                    title=_("Regular expression"),
                                    help=_("Must contain at least one subgroup <tt>(...)</tt>"),
                                    mingroups=0,
                                    maxgroups=9,
                                    size=30,
                                    allow_empty=False,
                                    mode=RegExp.prefix,
                                    case_sensitive=False,
                                ),
                                TextInput(
                                    title=_("Replacement"),
                                    help=_(
                                        "Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"
                                    ),
                                    size=30,
                                    allow_empty=False,
                                ),
                            ],
                        ),
                        title=_("Assign via regular expressions"),
                        help=_(
                            "You can add any number of expressions here which are executed succesively until the first match. "
                            "Please specify a regular expression in the first field. This expression should at "
                            "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                            "In the second field you specify the translated aggregation and can refer to the first matched "
                            "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                            ""
                        ),
                        add_label=_("Add expression"),
                        movable=False,
                    ),
                ),
            ],
        )

    def _vs_filters(self) -> Dictionary:
        return Dictionary(
            elements=[
                (
                    "aggr_name",
                    ListOf(
                        valuespec=TextInput(title=_("Pattern")),
                        title=_("By aggregation name (exact match)"),
                        add_label=_("Add new aggregation"),
                        movable=False,
                    ),
                ),
                (
                    "aggr_group_prefix",
                    ListOf(
                        valuespec=DropdownChoice(choices=bi.aggregation_group_choices),
                        title=_("By aggregation group prefix"),
                        add_label=_("Add new group"),
                        movable=False,
                    ),
                ),
            ],
            title=_("Filter aggregations"),
        )

    def _vs_options(self):
        return Dictionary(
            elements=[
                (
                    "state_scheduled_downtime",
                    MonitoringState(title=_("State, if BI aggregate is in scheduled downtime")),
                ),
                (
                    "state_acknowledged",
                    MonitoringState(title=_("State, if BI aggregate is acknowledged")),
                ),
            ],
            optional_keys=["state_scheduled_downtime", "state_acknowledged"],
            title=_("Additional options"),
        )


def _valuespec_special_agents_bi():
    _AgentBIOptions = dict[Literal["options"], Sequence[Mapping[str, object]]]

    def to_valuespec(x: Sequence[Mapping[str, object]] | _AgentBIOptions) -> _AgentBIOptions:
        return {"options": x} if isinstance(x, Sequence) else x

    return Migrate(
        valuespec=Dictionary(
            title=_("BI Aggregations"),
            elements=[
                (
                    "options",
                    ListOf(
                        valuespec=MultisiteBiDatasource().get_valuespec(),
                        help=_(
                            "This rule allows you to check multiple BI aggregations from multiple sites at once. "
                            "You can also assign aggregations to specific hosts through the piggyback mechanism."
                        ),
                    ),
                )
            ],
            optional_keys=False,
        ),
        migrate=to_valuespec,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name=RuleGroup.SpecialAgents("bi"),
        valuespec=_valuespec_special_agents_bi,
    )
)
