#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.veeam.agent_based.veeam_backup_jobs import (
    check_plugin_veeam_backup_jobs,
    DEFAULT_PARAMETERS,
)
from cmk.plugins.veeam.rulesets.backup_jobs import rule_spec_veeam_backup_jobs
from cmk.rulesets.v1.form_specs import DefaultValue, LevelsType, ServiceState, SimpleLevels


def test_the_rule_prefills_the_plugins_default() -> None:
    form = rule_spec_veeam_backup_jobs.parameter_form().elements["disabled_state"]
    assert isinstance(form.parameter_form, ServiceState)

    assert form.parameter_form.prefill == DefaultValue(DEFAULT_PARAMETERS["disabled_state"])


def test_the_rule_prefills_no_age_levels_like_the_plugins_default() -> None:
    form = rule_spec_veeam_backup_jobs.parameter_form().elements["age"]
    assert isinstance(form.parameter_form, SimpleLevels)

    assert DEFAULT_PARAMETERS["age"] == ("no_levels", None)
    assert form.parameter_form.prefill_levels_type == DefaultValue(LevelsType.NONE)


def test_the_rule_is_used_by_the_check_plugin() -> None:
    assert check_plugin_veeam_backup_jobs.check_ruleset_name == rule_spec_veeam_backup_jobs.name
