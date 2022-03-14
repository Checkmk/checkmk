#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, MonitoringState, Percentage, Tuple


def _parameter_valuespec_elasticsearch_cluster_health():
    return Dictionary(
        elements=[
            (
                "green",
                MonitoringState(
                    title=_("Status: green"),
                    default_value=0,
                ),
            ),
            (
                "yellow",
                MonitoringState(
                    title=_("Status: yellow"),
                    default_value=1,
                ),
            ),
            (
                "red",
                MonitoringState(
                    title=_("Status: red"),
                    default_value=2,
                ),
            ),
            (
                "number_of_nodes",
                Tuple(
                    title=_("Expected number of nodes"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="nodes"),
                        Integer(title=_("Critical if less then"), unit="nodes"),
                    ],
                ),
            ),
            (
                "number_of_data_nodes",
                Tuple(
                    title=_("Expected number of data nodes"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="nodes"),
                        Integer(title=_("Critical if less then"), unit="nodes"),
                    ],
                ),
            ),
        ],
        optional_keys=["number_of_nodes", "number_of_data_nodes", "green", "yellow", "red"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="elasticsearch_cluster_health",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_elasticsearch_cluster_health,
        title=lambda: _("Elasticsearch Cluster Health"),
    )
)


def _parameter_valuespec_elasticsearch_cluster_shards():
    return Dictionary(
        elements=[
            (
                "active_shards",
                Tuple(
                    title=_("Expected number of active shards in absolute number"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="shards"),
                        Integer(title=_("Critical if less then"), unit="shards"),
                    ],
                ),
            ),
            (
                "active_shards_percent_as_number",
                Tuple(
                    title=_("Expected number of active shards in percentage"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("%")),
                        Percentage(title=_("Critical at"), unit=_("%")),
                    ],
                ),
            ),
            (
                "active_primary_shards",
                Tuple(
                    title=_("Expected number of active primary shards"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="shards"),
                        Integer(title=_("Critical if less then"), unit="shards"),
                    ],
                ),
            ),
            (
                "unassigned_shards",
                Tuple(
                    title=_("Number of unassigned shards"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
            (
                "initializing_shards",
                Tuple(
                    title=_("Number of initializing shards"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
            (
                "relocating_shards",
                Tuple(
                    title=_("Number of relocating shards"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
            (
                "delayed_unassigned_shards",
                Tuple(
                    title=_("Number of delayed unassigned shards"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
            (
                "number_of_in_flight_fetch",
                Tuple(
                    title=_("Number of ongoing shard info requests"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
        ],
        optional_keys=[
            "active_shards",
            "active_shards_percent_as_number",
            "active_primary_shards",
            "unassigned_shards",
            "initializing_shards",
            "relocating_shards",
            "delayed_unassigned_shards",
            "number_of_in_flight_fetch",
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="elasticsearch_cluster_shards",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_elasticsearch_cluster_shards,
        title=lambda: _("Elasticsearch Cluster Shards"),
    )
)


def _parameter_valuespec_elasticsearch_cluster_tasks():
    return Dictionary(
        elements=[
            (
                "number_of_pending_tasks",
                Tuple(
                    title=_("Number of pending tasks"),
                    elements=[
                        Integer(title=_("Warning at"), unit="tasks"),
                        Integer(title=_("Critical at"), unit="tasks"),
                    ],
                ),
            ),
            (
                "task_max_waiting_in_queue_millis",
                Tuple(
                    title=_("Task max waiting"),
                    elements=[
                        Integer(title=_("Warning at"), unit="tasks"),
                        Integer(title=_("Critical at"), unit="tasks"),
                    ],
                ),
            ),
        ],
        optional_keys=["number_of_pending_tasks", "task_max_waiting_in_queue_millis"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="elasticsearch_cluster_tasks",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_elasticsearch_cluster_tasks,
        title=lambda: _("Elasticsearch Cluster Tasks"),
    )
)
