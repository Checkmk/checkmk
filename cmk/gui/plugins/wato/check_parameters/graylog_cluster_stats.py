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
from cmk.gui.valuespec import Dictionary, Filesize, Integer, MonitoringState, Tuple


def _parameter_valuespec_graylog_cluster_stats():
    return Dictionary(
        elements=[
            (
                "input_count_lower",
                Tuple(
                    title=_("Total number of inputs lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="inputs"),
                        Integer(title=_("Critical if less then"), unit="inputs"),
                    ],
                ),
            ),
            (
                "input_count_upper",
                Tuple(
                    title=_("Total number of inputs upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="inputs"),
                        Integer(title=_("Critical at"), unit="inputs"),
                    ],
                ),
            ),
            (
                "output_count_lower",
                Tuple(
                    title=_("Total number of outputs lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="outputs"),
                        Integer(title=_("Critical if less then"), unit="outputs"),
                    ],
                ),
            ),
            (
                "output_count_upper",
                Tuple(
                    title=_("Total number of outputs upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="outputs"),
                        Integer(title=_("Critical at"), unit="outputs"),
                    ],
                ),
            ),
            (
                "stream_count_lower",
                Tuple(
                    title=_("Total number of streams lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="streams"),
                        Integer(title=_("Critical if less then"), unit="streams"),
                    ],
                ),
            ),
            (
                "stream_count_upper",
                Tuple(
                    title=_("Total number of streams upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="streams"),
                        Integer(title=_("Critical at"), unit="streams"),
                    ],
                ),
            ),
            (
                "stream_rule_count_lower",
                Tuple(
                    title=_("Total number of stream rules lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="streams"),
                        Integer(title=_("Critical if less then"), unit="streams"),
                    ],
                ),
            ),
            (
                "stream_rule_count_upper",
                Tuple(
                    title=_("Total number of stream rules upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="streams"),
                        Integer(title=_("Critical at"), unit="streams"),
                    ],
                ),
            ),
            (
                "extractor_count_lower",
                Tuple(
                    title=_("Total number of extractor lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="extractor"),
                        Integer(title=_("Critical if less then"), unit="extractor"),
                    ],
                ),
            ),
            (
                "extractor_count_upper",
                Tuple(
                    title=_("Total number of extractor upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="extractor"),
                        Integer(title=_("Critical at"), unit="extractor"),
                    ],
                ),
            ),
            (
                "user_count_lower",
                Tuple(
                    title=_("Total number of user lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="user"),
                        Integer(title=_("Critical if less then"), unit="user"),
                    ],
                ),
            ),
            (
                "user_count_upper",
                Tuple(
                    title=_("Total number of user upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="user"),
                        Integer(title=_("Critical at"), unit="user"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_cluster_stats",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_cluster_stats,
        title=lambda: _("Graylog cluster statistics"),
    )
)


def _parameter_valuespec_graylog_cluster_stats_elastic():
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
                "number_of_nodes_lower",
                Tuple(
                    title=_("Total number of nodes lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="nodes"),
                        Integer(title=_("Critical if less then"), unit="nodes"),
                    ],
                ),
            ),
            (
                "number_of_nodes_upper",
                Tuple(
                    title=_("Total number of nodes upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="nodes"),
                        Integer(title=_("Critical at"), unit="nodes"),
                    ],
                ),
            ),
            (
                "number_of_data_nodes_lower",
                Tuple(
                    title=_("Total number of data nodes lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="data nodes"),
                        Integer(title=_("Critical if less then"), unit="data nodes"),
                    ],
                ),
            ),
            (
                "number_of_data_nodes_upper",
                Tuple(
                    title=_("Total number of data nodes upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="data nodes"),
                        Integer(title=_("Critical at"), unit="data nodes"),
                    ],
                ),
            ),
            (
                "active_shards_lower",
                Tuple(
                    title=_("Total number of active shards lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="shards"),
                        Integer(title=_("Critical if less then"), unit="shards"),
                    ],
                ),
            ),
            (
                "active_shards_upper",
                Tuple(
                    title=_("Total number of active shards upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
            (
                "active_primary_shards_lower",
                Tuple(
                    title=_("Total number of active primary shards lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="shards"),
                        Integer(title=_("Critical if less then"), unit="shards"),
                    ],
                ),
            ),
            (
                "active_primary_shards_upper",
                Tuple(
                    title=_("Total number of active primary shards upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
            (
                "unassigned_shards_upper",
                Tuple(
                    title=_("Total number of unassigned shards"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
            (
                "initializing_shards_upper",
                Tuple(
                    title=_("Number of initializing shards"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
            (
                "relocating_shards_upper",
                Tuple(
                    title=_("Number of relocating shards"),
                    elements=[
                        Integer(title=_("Warning at"), unit="shards"),
                        Integer(title=_("Critical at"), unit="shards"),
                    ],
                ),
            ),
            (
                "number_of_pending_tasks_upper",
                Tuple(
                    title=_("Number of pending tasks"),
                    elements=[
                        Integer(title=_("Warning at"), unit="tasks"),
                        Integer(title=_("Critical at"), unit="tasks"),
                    ],
                ),
            ),
            (
                "index_count_lower",
                Tuple(
                    title=_("Total number of indices lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="indices"),
                        Integer(title=_("Critical if less then"), unit="indices"),
                    ],
                ),
            ),
            (
                "index_count_upper",
                Tuple(
                    title=_("Total number of indices upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="indices"),
                        Integer(title=_("Critical at"), unit="indices"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_cluster_stats_elastic",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_cluster_stats_elastic,
        title=lambda: _("Graylog cluster elasticsearch statistics"),
    )
)


def _parameter_valuespec_graylog_cluster_stats_mongodb():
    return Dictionary(
        elements=[
            (
                "indexes_lower",
                Tuple(
                    title=_("Total number of indexes lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="indexes"),
                        Integer(title=_("Critical if less then"), unit="indexes"),
                    ],
                ),
            ),
            (
                "indexes_upper",
                Tuple(
                    title=_("Total number of indexes upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="indexes"),
                        Integer(title=_("Critical at"), unit="indexes"),
                    ],
                ),
            ),
            (
                "storage_size_upper",
                Tuple(
                    title=_("Upper levels for allocated storage size"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "index_size_upper",
                Tuple(
                    title=_("Upper levels for total index size"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "data_size_upper",
                Tuple(
                    title=_("Upper levels for total uncompressed data size"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "file_size_upper",
                Tuple(
                    title=_("Upper levels for data file size"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "ns_size_mb_upper",
                Tuple(
                    title=_("Upper levels for total namespace size"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "avg_obj_size_upper",
                Tuple(
                    title=_("Upper levels for average document size"),
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "num_extents_lower",
                Tuple(
                    title=_("Total number of extents lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="extents"),
                        Integer(title=_("Critical if less then"), unit="extents"),
                    ],
                ),
            ),
            (
                "num_extents_upper",
                Tuple(
                    title=_("Total number of extents upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="extents"),
                        Integer(title=_("Critical at"), unit="extents"),
                    ],
                ),
            ),
            (
                "collections_lower",
                Tuple(
                    title=_("Total number of collections lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="collections"),
                        Integer(title=_("Critical if less then"), unit="collections"),
                    ],
                ),
            ),
            (
                "collections_upper",
                Tuple(
                    title=_("Total number of collections upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="collections"),
                        Integer(title=_("Critical at"), unit="collections"),
                    ],
                ),
            ),
            (
                "ojects_lower",
                Tuple(
                    title=_("Total number of objects lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="objects"),
                        Integer(title=_("Critical if less then"), unit="objects"),
                    ],
                ),
            ),
            (
                "objects_upper",
                Tuple(
                    title=_("Total number of objects upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="objects"),
                        Integer(title=_("Critical at"), unit="objects"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_cluster_stats_mongodb",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_cluster_stats_mongodb,
        title=lambda: _("Graylog cluster mongodb statistics"),
    )
)
