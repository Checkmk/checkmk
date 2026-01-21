#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, RuleConditions, RuleOptions, Ruleset, RulesetCollection
from cmk.gui.watolib.sample_config import PS_DISCOVERY_RULES
from cmk.gui.watolib.sample_config._constants import _PS_COMMON_OPTS
from cmk.update_config.plugins.actions.rulesets_add_ps_discovery import (
    add_ps_discovery_rules,
    AUTOMATION_HELPER_RULE_ID,
    overwrite_ps_discovery_rules,
    PS_DISCOVERY_RULE_NAME,
    RABBITMQ_RULE_ID,
    UI_JOB_SCHEDULER_RULE_ID,
)


def _make_ruleset_collection_with_preexisting_rule(id_: str) -> RulesetCollection:
    # add some rule, but not quite one of ours:
    ruleset = Ruleset(PS_DISCOVERY_RULE_NAME)
    folder = folder_tree().root_folder()
    rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
    rule.id = id_
    ruleset.append_rule(folder, rule)
    return RulesetCollection({ruleset.name: ruleset})


@pytest.mark.usefixtures("request_context")
def test_update_without_preexisting_rulesets() -> None:
    rulesets = _make_ruleset_collection_with_preexisting_rule(
        "some other id, not one of the shipped rules"
    )
    assert rulesets.get_rulesets()[PS_DISCOVERY_RULE_NAME].num_rules() == 1

    add_ps_discovery_rules(logging.getLogger(), rulesets)
    assert (
        rulesets.get_rulesets()[PS_DISCOVERY_RULE_NAME].num_rules() == len(PS_DISCOVERY_RULES) + 1
    )


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    ["preexisting_rule_id", "expected_num_rules", "expected_rule_match"],
    [
        pytest.param(
            UI_JOB_SCHEDULER_RULE_ID,
            1,
            None,
            id="new default rule already present",
        ),
        pytest.param(
            PS_DISCOVERY_RULES[0]["id"],
            2,
            "~.*cmk-ui-job-scheduler.*",
            id="some other preexisting rule, add new default",
        ),
    ],
)
def test_update_with_preexisting_rulesets(
    preexisting_rule_id: str, expected_num_rules: int, expected_rule_match: str
) -> None:
    rulesets = _make_ruleset_collection_with_preexisting_rule(preexisting_rule_id)
    assert rulesets.get_rulesets()[PS_DISCOVERY_RULE_NAME].num_rules() == 1

    add_ps_discovery_rules(logging.getLogger(), rulesets)

    assert rulesets.get_rulesets()[PS_DISCOVERY_RULE_NAME].num_rules() == expected_num_rules
    rule = rulesets.get_rulesets()[PS_DISCOVERY_RULE_NAME].get_rule_by_id(UI_JOB_SCHEDULER_RULE_ID)
    assert rule.value.get("match", None) == expected_rule_match


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    ["rule_id", "preexisting", "expected"],
    [
        pytest.param(
            RABBITMQ_RULE_ID,
            None,
            "~(?:.*bin/rabbitmq-server)",
            id="no preexisting rule for rabbitmq",
        ),
        pytest.param(
            RABBITMQ_RULE_ID,
            "~(?:/omd/versions/.*/lib/erlang)|(?:.*bin/rabbitmq)",
            "~(?:.*bin/rabbitmq-server)",
            id="overwrite old default value in rule for rabbitmq",
        ),
        pytest.param(
            RABBITMQ_RULE_ID,
            "foobar",
            "foobar",
            id="keep manually changed value in rule for rabbitmq",
        ),
        pytest.param(
            AUTOMATION_HELPER_RULE_ID,
            None,
            "~.*cmk-automation-helper.*",
            id="no preexisting rule for automation helper",
        ),
        pytest.param(
            AUTOMATION_HELPER_RULE_ID,
            "~gunicorn:.*automation-helper",
            "~.*cmk-automation-helper.*",
            id="overwrite old default value in rule for automation helper",
        ),
        pytest.param(
            AUTOMATION_HELPER_RULE_ID,
            "foobar",
            "foobar",
            id="keep manually changed value in rule for automation helper",
        ),
    ],
)
def test_update_rule_default(rule_id: str, preexisting: str | None, expected: str) -> None:
    ruleset = Ruleset(PS_DISCOVERY_RULE_NAME)
    if preexisting is not None:
        folder = folder_tree().root_folder()
        ruleset.append_rule(
            folder,
            Rule(
                id_=rule_id,
                folder=folder,
                ruleset=ruleset,
                conditions=RuleConditions(folder.path()),
                options=RuleOptions(
                    disabled=False,
                    description="",
                    comment="",
                    docu_url="",
                    predefined_condition_id=None,
                ),
                value={"descr": "Something", "match": preexisting, **_PS_COMMON_OPTS},
            ),
        )

    overwrite_ps_discovery_rules(
        logging.getLogger(), RulesetCollection({PS_DISCOVERY_RULE_NAME: ruleset})
    )

    if preexisting is None:
        assert ruleset.num_rules() == 0
    else:
        assert ruleset.num_rules() == 1
        rule = ruleset.get_rule_by_id(rule_id)
        assert rule.value["match"] == expected
