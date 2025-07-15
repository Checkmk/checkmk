#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.plugins.wato.check_parameters import kube_node_container_count
from cmk.gui.plugins.wato.utils import rulespec_registry
from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib.rulespecs import ManualCheckParameterRulespec

SECTION_ELEMENTS = "running", "waiting", "terminated", "total"

OPTIONS = [
    f"{container_state}_{level_type}"
    for container_state in SECTION_ELEMENTS
    for level_type in ["upper", "lower"]
]


def test_parameter_valuespec_returns_a_dictionary() -> None:
    parameters = kube_node_container_count._parameter_valuespec()
    assert isinstance(parameters, Dictionary)


def test_parameter_valuespec_has_help() -> None:
    parameters = kube_node_container_count._parameter_valuespec()
    assert all(c in parameters.help() for c in SECTION_ELEMENTS)


def test_parameter_valuespec_has_as_much_elements_as_section_elements() -> None:
    parameters = kube_node_container_count._parameter_valuespec()
    assert len(parameters._elements()) == len(OPTIONS)


@pytest.mark.parametrize("section_element", OPTIONS)
def test_parameter_valuespec_has_element_for_section_element(
    section_element: str,
) -> None:
    parameters = kube_node_container_count._parameter_valuespec()
    assert any(title == section_element for title, _ in parameters._elements())


@pytest.fixture
def rulespec():
    for r in rulespec_registry.get_by_group("static/applications"):
        if r.name == RuleGroup.StaticChecks("kube_node_container_count"):
            return r
    assert False, "Should be able to find the rulespec"


@pytest.mark.xfail(reason="`match_type` should be dict")
def test_rulespec_registry_match_type(rulespec: ManualCheckParameterRulespec) -> None:
    assert rulespec.match_type == "dict"


def test_rulespec_registry_parameter_valuespec(rulespec: ManualCheckParameterRulespec) -> None:
    assert rulespec._parameter_valuespec == kube_node_container_count._parameter_valuespec


def test_rulespec_registry_title(rulespec: ManualCheckParameterRulespec) -> None:
    assert rulespec.title == "Kubernetes node containers"
