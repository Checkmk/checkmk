#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.wato.special_agents.aws import AWSSpecialAgentValuespecBuilder


def test_plus_only_services_present_in_plus_edition():
    valuespec_builder = AWSSpecialAgentValuespecBuilder(plus_edition=True)
    regional_services = valuespec_builder.get_regional_services()
    global_services = valuespec_builder.get_global_services()

    assert "sns" in {service[0] for service in regional_services}
    assert "cloudfront" in {service[0] for service in global_services}


def test_plus_only_services_not_present_in_enterprise_edition():
    valuespec_builder = AWSSpecialAgentValuespecBuilder(plus_edition=False)
    regional_services = valuespec_builder.get_regional_services()
    global_services = valuespec_builder.get_global_services()

    assert "sns" not in {service[0] for service in regional_services}
    assert "cloudfront" not in {service[0] for service in global_services}
