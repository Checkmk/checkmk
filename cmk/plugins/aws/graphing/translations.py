#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translation

translation_aws_network = translation.Translation(
    "aws_network",
    [
        translation.PassiveCheck("aws_ec2_network_io"),
        translation.PassiveCheck("aws_rds_network_io"),
    ],
    {
        "in": translation.RenamingAndScaling(
            "if_in_bps",
            8,
        ),
        "inbcast": translation.Renaming("if_in_bcast"),
        "indisc": translation.Renaming("if_in_discards"),
        "inerr": translation.Renaming("if_in_errors"),
        "inmcast": translation.Renaming("if_in_mcast"),
        "innucast": translation.Renaming("if_in_non_unicast"),
        "inucast": translation.Renaming("if_in_unicast"),
        "out": translation.RenamingAndScaling(
            "if_out_bps",
            8,
        ),
        "outbcast": translation.Renaming("if_out_bcast"),
        "outdisc": translation.Renaming("if_out_discards"),
        "outerr": translation.Renaming("if_out_errors"),
        "outmcast": translation.Renaming("if_out_mcast"),
        "outnucast": translation.Renaming("if_out_non_unicast"),
        "outucast": translation.Renaming("if_out_unicast"),
        "total": translation.RenamingAndScaling(
            "if_total_bps",
            8,
        ),
    },
)

translation_aws_http = translation.Translation(
    "aws_http",
    [
        translation.PassiveCheck("aws_elb_http_elb"),
        translation.PassiveCheck("aws_elb_http_backend"),
        translation.PassiveCheck("aws_elbv2_application_http_elb"),
        translation.PassiveCheck("aws_s3_requests_http_errors"),
    ],
    {
        "http_4xx_perc": translation.Renaming("aws_http_4xx_perc"),
        "http_4xx_rate": translation.Renaming("aws_http_4xx_rate"),
        "http_5xx_perc": translation.Renaming("aws_http_5xx_perc"),
        "http_5xx_rate": translation.Renaming("aws_http_5xx_rate"),
    },
)

translation_aws_elb_backend_connection_errors = translation.Translation(
    "aws_elb_backend_connection_errors",
    [translation.PassiveCheck("aws_elb_backend_connection_errors")],
    {"backend_connection_errors_rate": translation.Renaming("aws_backend_connection_errors_rate")},
)

translation_aws_elbv2_application_connections = translation.Translation(
    "aws_elbv2_application_connections",
    [translation.PassiveCheck("aws_elbv2_application_connections")],
    {
        "aws_Active_connections": translation.Renaming("aws_active_connections"),
        "aws_New_connections": translation.Renaming("aws_new_connections"),
        "aws_Rejected_connections": translation.Renaming("aws_rejected_connections"),
        "aws_TLS errors_connections": translation.Renaming("aws_client_tls_errors"),
    },
)
