#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, ValueSpec

# A notes about the names of the Dictionary elements. They correspond to the names of the metrics in
# the check plugin. Please do not change them.


def _vs_gcs_bucket_requests() -> ValueSpec:
    return Dictionary(
        title=_("Parameters for the bucket requests"),
        elements=[
            ("requests", Levels(title=_("Parameters for the bucket requests"), unit="1/second"))
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_gcs_requests",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gcs_bucket_requests,
        title=lambda: _("GCP/GCS Requests"),
    )
)


def _vs_gcs_bucket_network() -> ValueSpec:
    return Dictionary(
        title=_("Parameters for the bucket network io"),
        elements=[
            ("net_data_sent", Levels(title=_("Parameters send bytes"), unit="bytes/s")),
            ("net_data_recv", Levels(title=_("Parameters received bytes"), unit="bytes/s")),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_gcs_network",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gcs_bucket_network,
        title=lambda: _("GCP/GCS Network"),
    )
)


def _vs_gcs_bucket_objects() -> ValueSpec:
    return Dictionary(
        title=_("Parameters for the bucket objects io"),
        elements=[
            ("aws_bucket_size", Levels(title=_("Parameters of total bucket size"), unit="bytes")),
            ("aws_num_objects", Levels(title=_("Parameters of bucket object counts"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_gcs_objects",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gcs_bucket_objects,
        title=lambda: _("GCP/GCS Objects"),
    )
)


def _vs_function_instances() -> ValueSpec:
    return Dictionary(
        title=_("Levels on instances"),
        elements=[
            ("aws_lambda_provisioned_concurrent_executions", Levels(title=_("instances"))),
            ("aws_lambda_concurrent_executions", Levels(title=_("active instances"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_function_instances",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_function_instances,
        title=lambda: _("GCP/Function instances"),
    )
)


def _vs_function_execution() -> ValueSpec:
    return Dictionary(
        title=_("Levels on performance"),
        elements=[
            ("execution_count", Levels(title=_("execution count"))),
            ("aws_lambda_memory_size_absolute", Levels(title=_("memory"))),
            ("aws_lambda_duration", Levels(title=_("execution time"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_function_execution",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_function_execution,
        title=lambda: _("GCP/Function execution"),
    )
)


def _vs_function_egress() -> ValueSpec:
    return Dictionary(
        title=_("Levels on network egress"),
        elements=[
            ("net_data_sent", Levels(title=_("instances"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_function_egress",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_function_egress,
        title=lambda: _("GCP/Function egress"),
    )
)
