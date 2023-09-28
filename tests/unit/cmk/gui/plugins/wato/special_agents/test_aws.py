#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.special_agents.aws import AWSSpecialAgentValuespecBuilder
from cmk.gui.plugins.wato.special_agents.common import aws_region_to_monitor


def test_cloud_only_services_present_in_cloud_edition():
    valuespec_builder = AWSSpecialAgentValuespecBuilder(cloud_edition=True)
    regional_services = valuespec_builder.get_regional_services()
    global_services = valuespec_builder.get_global_services()

    assert "sns" in {service[0] for service in regional_services}
    assert "cloudfront" in {service[0] for service in global_services}


def test_cloud_only_services_not_present_in_enterprise_edition():
    valuespec_builder = AWSSpecialAgentValuespecBuilder(cloud_edition=False)
    regional_services = valuespec_builder.get_regional_services()
    global_services = valuespec_builder.get_global_services()

    assert "sns" not in {service[0] for service in regional_services}
    assert "cloudfront" not in {service[0] for service in global_services}


def test_display_order_logic() -> None:
    # Assemble
    display_regions = [display_region for _region_id, display_region in aws_region_to_monitor()]
    # Assert
    # GovCloud entries are generally useful to only very few people. Thus, they should all be
    # displayed at end of the list. Within the groups, the order should be alphabetical.
    assert display_regions == [
        *sorted(region for region in display_regions if "GovCloud" not in region),
        *sorted(region for region in display_regions if "GovCloud" in region),
    ]
