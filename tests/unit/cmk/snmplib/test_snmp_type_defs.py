#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from cmk.snmplib.type_defs import SNMPDetectSpec, SNMPRuleDependentDetectSpec
from cmk.utils.type_defs import RuleSetName


@pytest.mark.parametrize("rulesets, evaluator, expect_type_error", [
    (
        [RuleSetName('a'), RuleSetName('b')],
        lambda a, b: SNMPDetectSpec([[('.1.2.3.4.5', 'Foo.*', True)]]),
        False,
    ),
    (
        [],
        lambda: SNMPDetectSpec([[('.1.2.3.4.5', 'Foo.*', True)]]),
        False,
    ),
    (
        [RuleSetName('a'), RuleSetName('b')],
        lambda b, a: SNMPDetectSpec([[('.1.2.3.4.5', 'Foo.*', True)]]),
        True,
    ),
])
def test_snmp_rule_dependent_detect_spec(rulesets, evaluator, expect_type_error):
    if expect_type_error:
        with pytest.raises(TypeError):
            SNMPRuleDependentDetectSpec(
                rulesets,
                evaluator,
            )
    else:
        SNMPRuleDependentDetectSpec(
            rulesets,
            evaluator,
        )
