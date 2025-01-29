#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.gcp import _vs_network_elements, _vs_percentile_choice
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Filesize, TextInput, ValueSpec

# A notes about the names of the Dictionary elements. They correspond to the names of the metrics in
# the check plug-in. Please do not change them.


def _vs_gcs_bucket_requests() -> ValueSpec:
    return Dictionary(
        title=_("Parameters for the bucket requests"),
        elements=[
            ("requests", Levels(title=_("Parameters for the bucket requests"), unit="1/second"))
        ],
    )


def _item_spec_gcs() -> ValueSpec:
    return TextInput(title=_("Bucket"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_gcs_requests",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gcs_bucket_requests,
        title=lambda: _("GCP/GCS requests"),
        item_spec=_item_spec_gcs,
    )
)


def _vs_gcs_bucket_network() -> ValueSpec:
    return Dictionary(
        title=_("Parameters for the bucket network io"), elements=_vs_network_elements
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_gcs_network",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gcs_bucket_network,
        title=lambda: _("GCP/GCS network"),
        item_spec=_item_spec_gcs,
    )
)


def _vs_gcs_bucket_objects() -> ValueSpec:
    return Dictionary(
        title=_("Parameters for the bucket objects io"),
        elements=[
            (
                "aws_bucket_size",
                SimpleLevels(Filesize, title=_("Parameters of total bucket size")),
            ),
            ("aws_num_objects", Levels(title=_("Parameters of bucket object counts"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_gcs_objects",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gcs_bucket_objects,
        title=lambda: _("GCP/GCS objects"),
        item_spec=_item_spec_gcs,
    )
)


def _item_spec_http_lb() -> ValueSpec:
    return TextInput(title=_("Project"))


def _vs_gcs_http_lb_requests() -> ValueSpec:
    return Dictionary(
        title=_("Parameters for the  requests"),
        elements=[("requests", Levels(title=_("Parameters for the requests"), unit="1/second"))],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_http_lb_requests",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gcs_http_lb_requests,
        title=lambda: _("GCP/HTTP(S) load balancer requests"),
        item_spec=_item_spec_http_lb,
    )
)


def _vs_gcs_http_lb_latencies() -> ValueSpec:
    return Dictionary(
        title=_("Parameters for the latencies"),
        elements=[
            (
                "latencies",
                _vs_percentile_choice("Parameters for the latencies", "Latencies", "second"),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="gcp_http_lb_latencies",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_vs_gcs_http_lb_latencies,
        title=lambda: _("GCP/HTTP(S) load balancer latencies"),
        item_spec=_item_spec_http_lb,
    )
)
