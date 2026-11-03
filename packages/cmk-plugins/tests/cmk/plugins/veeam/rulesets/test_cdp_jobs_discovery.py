#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.veeam.agent_based.veeam_cdp_jobs import (
    check_plugin_veeam_cdp_jobs,
    DEFAULT_DISCOVERY_PARAMETERS,
)
from cmk.plugins.veeam.rulesets.cdp_jobs_discovery import rule_spec_discovery_veeam_cdp_jobs
from cmk.rulesets.v1.form_specs import BooleanChoice, DefaultValue


def test_the_rule_prefills_the_plugins_discovery_default() -> None:
    form = rule_spec_discovery_veeam_cdp_jobs.parameter_form().elements["discover_disabled"]
    assert isinstance(form.parameter_form, BooleanChoice)

    assert form.parameter_form.prefill == DefaultValue(
        DEFAULT_DISCOVERY_PARAMETERS["discover_disabled"]
    )


def test_the_rule_is_used_by_the_check_plugin() -> None:
    assert (
        check_plugin_veeam_cdp_jobs.discovery_ruleset_name
        == rule_spec_discovery_veeam_cdp_jobs.name
    )
