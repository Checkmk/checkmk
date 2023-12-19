#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations

translation_aws_network = translations.Translation(
    name="aws_network",
    check_commands=[
        translations.PassiveCheck("aws_ec2_network_io"),
        translations.PassiveCheck("aws_rds_network_io"),
    ],
    translations={
        "in": translations.RenamingAndScaling(
            "if_in_bps",
            8,
        ),
        "inbcast": translations.Renaming("if_in_bcast"),
        "indisc": translations.Renaming("if_in_discards"),
        "inerr": translations.Renaming("if_in_errors"),
        "inmcast": translations.Renaming("if_in_mcast"),
        "innucast": translations.Renaming("if_in_non_unicast"),
        "inucast": translations.Renaming("if_in_unicast"),
        "out": translations.RenamingAndScaling(
            "if_out_bps",
            8,
        ),
        "outbcast": translations.Renaming("if_out_bcast"),
        "outdisc": translations.Renaming("if_out_discards"),
        "outerr": translations.Renaming("if_out_errors"),
        "outmcast": translations.Renaming("if_out_mcast"),
        "outnucast": translations.Renaming("if_out_non_unicast"),
        "outucast": translations.Renaming("if_out_unicast"),
        "total": translations.RenamingAndScaling(
            "if_total_bps",
            8,
        ),
    },
)

translation_aws_http = translations.Translation(
    name="aws_http",
    check_commands=[
        translations.PassiveCheck("aws_elb_http_elb"),
        translations.PassiveCheck("aws_elb_http_backend"),
        translations.PassiveCheck("aws_elbv2_application_http_elb"),
        translations.PassiveCheck("aws_s3_requests_http_errors"),
    ],
    translations={
        "http_4xx_perc": translations.Renaming("aws_http_4xx_perc"),
        "http_4xx_rate": translations.Renaming("aws_http_4xx_rate"),
        "http_5xx_perc": translations.Renaming("aws_http_5xx_perc"),
        "http_5xx_rate": translations.Renaming("aws_http_5xx_rate"),
    },
)

translation_aws_elb_backend_connection_errors = translations.Translation(
    name="aws_elb_backend_connection_errors",
    check_commands=[translations.PassiveCheck("aws_elb_backend_connection_errors")],
    translations={
        "backend_connection_errors_rate": translations.Renaming(
            "aws_backend_connection_errors_rate"
        )
    },
)

translation_aws_elbv2_application_connections = translations.Translation(
    name="aws_elbv2_application_connections",
    check_commands=[translations.PassiveCheck("aws_elbv2_application_connections")],
    translations={
        "aws_Active_connections": translations.Renaming("aws_active_connections"),
        "aws_New_connections": translations.Renaming("aws_new_connections"),
        "aws_Rejected_connections": translations.Renaming("aws_rejected_connections"),
        "aws_TLS errors_connections": translations.Renaming("aws_client_tls_errors"),
    },
)
