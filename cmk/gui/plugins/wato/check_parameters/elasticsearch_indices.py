#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CascadingDropdown,
    CheckParameterRulespecWithItem,
    FixedValue,
    HostRulespec,
    ListOf,
    RegExp,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Dictionary, Integer, Percentage, TextInput, Tuple


def _parameter_valuespec_elasticsearch_indices_discovery() -> Dictionary:
    return Dictionary(
        title=_("Discovery of Elasticsearch indices"),
        elements=[
            (
                "grouping",
                CascadingDropdown(
                    title=_("Grouping of indices"),
                    help=_(
                        "Configure the grouping of indices. Elasticsearch can for example be "
                        "configured to automatically add a timestamp to index names, see "
                        '<a href=%s target="_blank">the documentation</a>. Via this grouping '
                        "option, Checkmk can e.g. be configured to accumulate all indices which "
                        "only differ in the trailing timestamp into a single service."
                    )
                    % '"https://www.elastic.co/guide/en/elasticsearch/reference/current/date-index-name-processor.html"',
                    choices=[
                        (
                            "enabled",
                            _("Group indices"),
                            ListOf(
                                valuespec=RegExp(mode="infix"),
                                help=_(
                                    "Group indices according to the following regular expressions. For each regular expression, Checkmk traverses through "
                                    "the list of indices reported by the Elasticsearch special agent. If an index matches, it is added to a group. The group "
                                    "name is determined by the part of the index name which matches the regular expression. For example, suppose you have the "
                                    "following five indices:"
                                    "<ul>"
                                    "<li>my-index-2022.10</li>"
                                    "<li>my-index-2022.11</li>"
                                    "<li>my-other-index-2021-01-01</li>"
                                    "<li>my-other-index-2021-01-02</li>"
                                    "<li>undated-index</li>"
                                    "</ul>"
                                    "Using the regular expression <tt>([a-z]|-)+[a-z]</tt>, you would configure the following groups:"
                                    "<ul>"
                                    "<li>my-index (contains my-index-2022.10, my-index-2022.11)</li>"
                                    "<li>my-other-index (contains my-other-index-2021-01-01, my-other-index-2021-01-02)</li>"
                                    "<li>undated-index (contains undated-index, so effectively ungrouped)</li>"
                                    "</ul>"
                                    "The same grouping could be achieved using the two regular expressions <tt>my-index</tt> and <tt>my-other-index</tt>, "
                                    "however, such a list can be cumbersome to maintain in case of a large number of indices. Note that indices which do not "
                                    "match any of the configured regular expressions will be discovered as single services. Conversely, any index that is part "
                                    "of at least one group will not be discovered as a single service."
                                ),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "disabled",
                            _("Do not group indices"),
                            FixedValue(
                                value=[],
                                totext="",
                            ),
                        ),
                    ],
                    sorted=False,
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="elasticsearch_indices_disovery",
        valuespec=_parameter_valuespec_elasticsearch_indices_discovery,
    )
)


def _parameter_valuespec_elasticsearch_indices():
    return Dictionary(
        elements=[
            (
                "elasticsearch_count_rate",
                Tuple(
                    title=_("Document count delta"),
                    help=_(
                        "If this parameter is set, the document count delta of the "
                        "last minute will be compared to the delta of the average X "
                        "minutes. You can set WARN or CRIT levels to check if the last "
                        "minute's delta is X percent higher than the average delta."
                    ),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("percent higher than average")),
                        Percentage(title=_("Critical at"), unit=_("percent higher than average")),
                        Integer(
                            title=_("Averaging"), unit=_("minutes"), minvalue=1, default_value=30
                        ),
                    ],
                ),
            ),
            (
                "elasticsearch_size_rate",
                Tuple(
                    title=_("Size delta"),
                    help=_(
                        "If this parameter is set, the size delta of the last minute "
                        "will be compared to the delta of the average X minutes. "
                        "You can set WARN or CRIT levels to check if the last minute's "
                        "delta is X percent higher than the average delta."
                    ),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("percent higher than average")),
                        Percentage(title=_("Critical at"), unit=_("percent higher than average")),
                        Integer(
                            title=_("Averaging"), unit=_("minutes"), minvalue=1, default_value=30
                        ),
                    ],
                ),
            ),
        ],
        ignored_keys=["grouping_regex"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="elasticsearch_indices",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of indice")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_elasticsearch_indices,
        title=lambda: _("Elasticsearch Indices"),
    )
)
