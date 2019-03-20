#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    MonitoringState,
    Percentage,
    Tuple,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
)


@rulespec_registry.register
class RulespecCheckgroupParametersElasticsearchClusterHealth(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "elasticsearch_cluster_health"

    @property
    def title(self):
        return _("Elasticsearch Cluster Health")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            elements=[
                ("green", MonitoringState(
                    title=_("Status: green"),
                    default_value=0,
                )),
                ("yellow", MonitoringState(
                    title=_("Status: yellow"),
                    default_value=1,
                )),
                ("red", MonitoringState(
                    title=_("Status: red"),
                    default_value=2,
                )),
                ("number_of_nodes",
                 Tuple(
                     title=_("Expected number of nodes"),
                     elements=[
                         Integer(title=_("Warning if less then"), unit="nodes"),
                         Integer(title=_("Critical if less then"), unit="nodes")
                     ],
                 )),
                ("number_of_data_nodes",
                 Tuple(
                     title=_("Expected number of data nodes"),
                     elements=[
                         Integer(title=_("Warning if less then"), unit="nodes"),
                         Integer(title=_("Critical if less then"), unit="nodes")
                     ],
                 )),
            ],
            optional_keys=["number_of_nodes", "number_of_data_nodes", "green", "yellow", "red"],
        )


@rulespec_registry.register
class RulespecCheckgroupParametersElasticsearchClusterShards(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "elasticsearch_cluster_shards"

    @property
    def title(self):
        return _("Elasticsearch Cluster Shards")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            elements=[
                ("active_shards",
                 Tuple(
                     title=_("Expected number of active shards in absolute number"),
                     elements=[
                         Integer(title=_("Warning if less then"), unit="shards"),
                         Integer(title=_("Critical if less then"), unit="shards")
                     ],
                 )),
                ("active_shards_percent_as_number",
                 Tuple(
                     title=_("Expected number of active shards in percentage"),
                     elements=[
                         Percentage(title=_("Warning at"), unit=_("%")),
                         Percentage(title=_("Critical at"), unit=_("%"))
                     ],
                 )),
                ("active_primary_shards",
                 Tuple(
                     title=_("Expected number of active primary shards"),
                     elements=[
                         Integer(title=_("Warning if less then"), unit="shards"),
                         Integer(title=_("Critical if less then"), unit="shards")
                     ],
                 )),
                ("unassigned_shards",
                 Tuple(
                     title=_("Number of unassigned shards"),
                     elements=[
                         Integer(title=_("Warning at"), unit="shards"),
                         Integer(title=_("Critical at"), unit="shards")
                     ],
                 )),
                ("initializing_shards",
                 Tuple(
                     title=_("Number of initializing shards"),
                     elements=[
                         Integer(title=_("Warning at"), unit="shards"),
                         Integer(title=_("Critical at"), unit="shards")
                     ],
                 )),
                ("relocating_shards",
                 Tuple(
                     title=_("Number of relocating shards"),
                     elements=[
                         Integer(title=_("Warning at"), unit="shards"),
                         Integer(title=_("Critical at"), unit="shards")
                     ],
                 )),
                ("delayed_unassigned_shards",
                 Tuple(
                     title=_("Number of delayed unassigned shards"),
                     elements=[
                         Integer(title=_("Warning at"), unit="shards"),
                         Integer(title=_("Critical at"), unit="shards")
                     ],
                 )),
                ("number_of_in_flight_fetch",
                 Tuple(
                     title=_("Number of ongoing shard info requests"),
                     elements=[
                         Integer(title=_("Warning at"), unit="shards"),
                         Integer(title=_("Critical at"), unit="shards")
                     ],
                 )),
            ],
            optional_keys=[
                "active_shards", "active_shards_percent_as_number", "active_primary_shards",
                "unassigned_shards", "initializing_shards", "relocating_shards",
                "delayed_unassigned_shards", "number_of_in_flight_fetch"
            ],
        )


@rulespec_registry.register
class RulespecCheckgroupParametersElasticsearchClusterTasks(CheckParameterRulespecWithoutItem):
    @property
    def group(self):
        return RulespecGroupCheckParametersApplications

    @property
    def check_group_name(self):
        return "elasticsearch_cluster_tasks"

    @property
    def title(self):
        return _("Elasticsearch Cluster Tasks")

    @property
    def match_type(self):
        return "dict"

    @property
    def parameter_valuespec(self):
        return Dictionary(
            elements=[
                ("number_of_pending_tasks",
                 Tuple(
                     title=_("Number of pending tasks"),
                     elements=[
                         Integer(title=_("Warning at"), unit="tasks"),
                         Integer(title=_("Critical at"), unit="tasks")
                     ],
                 )),
                ("task_max_waiting_in_queue_millis",
                 Tuple(
                     title=_("Task max waiting"),
                     elements=[
                         Integer(title=_("Warning at"), unit="tasks"),
                         Integer(title=_("Critical at"), unit="tasks")
                     ],
                 )),
            ],
            optional_keys=["number_of_pending_tasks", "task_max_waiting_in_queue_millis"],
        )
