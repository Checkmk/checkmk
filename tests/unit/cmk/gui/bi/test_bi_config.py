#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest
from pytest import param

from tests.unit.cmk.bi.bi_mocks import MockBIAggregationPack
from tests.unit.cmk.bi.bi_test_data import sample_config

from cmk.gui.bi._config import ModeBIEditRule
from cmk.gui.bi._valuespecs import _convert_bi_rule_from_vs, _convert_bi_rule_to_vs
from cmk.gui.exceptions import MKUserError


# This test covers the outermost TransformValuespec
# The value-part of the cascading dropdown valuespec_config still contains REST-like syntax
@pytest.mark.parametrize(
    "rest_config",
    [
        param(None, id="complain_phase_special_handling"),
        param(
            {
                "action": {
                    "params": {"arguments": []},
                    "rule_id": "applications",
                    "type": "call_a_rule",
                },
                "search": {"type": "empty"},
            },
            id="call_a_rule",
        ),
        param(
            {
                "action": {"host_regex": "test", "type": "state_of_host"},
                "search": {"type": "empty"},
            },
            id="state_of_host",
        ),
        param(
            {
                "action": {
                    "host_regex": "test",
                    "service_regex": "testservice",
                    "type": "state_of_service",
                },
                "search": {"type": "empty"},
            },
            id="state_of_service",
        ),
        param(
            {
                "action": {"host_regex": "testhost", "type": "state_of_remaining_services"},
                "search": {"type": "empty"},
            },
            id="state_of_remaining_services",
        ),
        param(
            {
                "action": {
                    "params": {"arguments": ["hostarg"]},
                    "rule_id": "applications",
                    "type": "call_a_rule",
                },
                "search": {
                    "conditions": {
                        "host_choice": {"type": "all_hosts"},
                        "host_folder": "",
                        "host_labels": {},
                        "host_tags": {},
                    },
                    "refer_to": "host",
                    "type": "host_search",
                },
            },
            id="host_search",
        ),
        param(
            {
                "action": {
                    "params": {"arguments": ["testhost"]},
                    "rule_id": "applications",
                    "type": "call_a_rule",
                },
                "search": {
                    "conditions": {
                        "host_choice": {"type": "all_hosts"},
                        "host_folder": "",
                        "host_labels": {},
                        "host_tags": {},
                        "service_labels": {},
                        "service_regex": "test",
                    },
                    "type": "service_search",
                },
            },
            id="service_search",
        ),
    ],
)
def test_bi_rule_outermost_transform_to_vs(rest_config: None | Mapping[str, object]) -> None:
    if rest_config is None:
        # Error page special handling
        # This handles html.var voodoo, never results in a rest config
        assert _convert_bi_rule_to_vs(rest_config) is None
        return

    assert _convert_bi_rule_from_vs(_convert_bi_rule_to_vs(rest_config)) == rest_config


class ModeBIEditRuleFake(ModeBIEditRule):
    """Fake for testing new bi rule edit"""

    def __init__(self):
        self._rule_id = None
        self._new = True

        self._bi_packs = MockBIAggregationPack(sample_config.bi_packs_config)
        self._bi_pack = None


def test_validate_rule_id() -> None:
    edit_rule_mode = ModeBIEditRuleFake()

    edit_rule_mode._validate_rule_id("unique_rule_id")

    with pytest.raises(MKUserError, match="There is already a rule with the ID <b>networking</b>."):
        edit_rule_mode._validate_rule_id("networking")
