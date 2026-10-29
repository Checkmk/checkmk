#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.generic_agent_options.rulesets.classic_file_deployment import (
    rule_spec_classic_file_deployment,
)


def test_classic_file_deployment_has_no_options() -> None:
    """CMK-40617 AC1"""
    assert not rule_spec_classic_file_deployment.parameter_form().elements


def test_classic_file_deployment_is_deprecated() -> None:
    """CMK-40617 AC2"""
    assert rule_spec_classic_file_deployment.is_deprecated
