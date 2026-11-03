#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Mapping

from cmk.checkengine.plugin_backend import filter_relevant_raw_sections
from cmk.checkengine.plugins import AgentBasedPlugins, SectionName, SectionPlugin


def test_all_sections_are_subscribed_by_some_plugin(
    agent_based_plugins: AgentBasedPlugins,
) -> None:
    """Test that all registered sections are subscribed to by some plugin

    We have very few sections that are not subscribed to by any plugin.
    We can afford to keep track of those.
    """
    allowed_unsubscribed_sections = {
        "labels",
        "azure_labels",
        "azure_v2_labels",
        "ec2_labels",
        "elb_generic_labels",
        "elbv2_generic_labels",
        "aws_v2_ec2_labels",
        "aws_v2_elb_generic_labels",
        "aws_v2_elbv2_generic_labels",
    }

    all_existing_sections: Mapping[SectionName, SectionPlugin] = {
        **agent_based_plugins.agent_sections,
        **agent_based_plugins.snmp_sections,
    }

    subscribed_sections_names = set(
        filter_relevant_raw_sections(
            consumers=itertools.chain(
                agent_based_plugins.check_plugins.values(),
                agent_based_plugins.inventory_plugins.values(),
            ),
            sections=all_existing_sections.values(),
        )
    )

    unsubscribed_sections_names = {
        str(n) for n in set(all_existing_sections) - subscribed_sections_names
    }

    assert unsubscribed_sections_names == allowed_unsubscribed_sections
