#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

AWS_REGIONS: Final = [
    # Changes to the right-hand side of this list cause the following user facing changes:
    # - Incompatible: the service name of the check `aws_status`
    # - Compatible: The displayed options in the rule `Amazon Web Services (AWS) status`
    #   are updated.
    ("af-south-1", "Africa (Cape Town)"),
    ("ap-east-1", "Asia Pacific (Hong Kong)"),
    ("ap-south-2", "Asia Pacific (Hyderabad)"),
    ("ap-southeast-3", "Asia Pacific (Jakarta)"),
    ("ap-south-1", "Asia Pacific (Mumbai)"),
    ("ap-northeast-3", "Asia Pacific (Osaka-Local)"),
    ("ap-northeast-2", "Asia Pacific (Seoul)"),
    ("ap-southeast-1", "Asia Pacific (Singapore)"),
    ("ap-southeast-2", "Asia Pacific (Sydney)"),
    ("ap-northeast-1", "Asia Pacific (Tokyo)"),
    ("ca-central-1", "Canada (Central)"),
    ("cn-north-1", "China (Beijing)"),
    ("cn-northwest-1", "China (Ningxia)"),
    ("eu-central-1", "Europe (Frankfurt)"),
    ("eu-west-1", "Europe (Ireland)"),
    ("eu-west-2", "Europe (London)"),
    ("eu-south-1", "Europe (Milan)"),
    ("eu-west-3", "Europe (Paris)"),
    ("eu-south-2", "Europe (Spain)"),
    ("eu-north-1", "Europe (Stockholm)"),
    ("eu-central-2", "Europe (Zurich)"),
    ("me-south-1", "Middle East (Bahrain)"),
    ("me-central-1", "Middle East (UAE)"),
    ("sa-east-1", "South America (Sao Paulo)"),
    ("us-east-1", "US East (N. Virginia)"),
    ("us-east-2", "US East (Ohio)"),
    ("us-west-1", "US West (N. California)"),
    ("us-west-2", "US West (Oregon)"),
    ("us-gov-east-1", "GovCloud (US-East)"),
    ("us-gov-west-1", "GovCloud (US-West)"),
]


def aws_region_to_monitor() -> list[tuple[str, str]]:
    def key(regionid_display: tuple[str, str]) -> str:
        return regionid_display[1]

    regions_by_display_order = [
        *sorted((r for r in AWS_REGIONS if "GovCloud" not in r[1]), key=key),
        *sorted((r for r in AWS_REGIONS if "GovCloud" in r[1]), key=key),
    ]
    return [(id_, f"{region} | {id_}") for id_, region in regions_by_display_order]
