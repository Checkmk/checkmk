#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name

import pytest

from cmk.gui.plugins.wato.check_parameters import kube_node_container_count
from cmk.gui.valuespec import Dictionary

SECTION_ELEMENTS = "running", "waiting", "terminated", "total"


def test_parameter_valuespec_returns_a_dictionary():
    parameters = kube_node_container_count._parameter_valuespec()
    assert isinstance(parameters, Dictionary)


def test_parameter_valuespec_has_help():
    parameters = kube_node_container_count._parameter_valuespec()
    assert all(c in parameters.help() for c in SECTION_ELEMENTS)


def test_parameter_valuespec_has_as_much_elements_as_section_elements():
    parameters = kube_node_container_count._parameter_valuespec()
    assert len(parameters._elements()) == len(SECTION_ELEMENTS)


@pytest.mark.parametrize("section_element", SECTION_ELEMENTS)
def test_parameter_valuespec_has_element_for_section_element(section_element):
    parameters = kube_node_container_count._parameter_valuespec()
    assert any(title == section_element for title, _ in parameters._elements())


@pytest.mark.parametrize("levels", ["levels_upper", "levels_lower"])
def test_parameter_valuespec_has_element_with_levels(levels):
    parameters = kube_node_container_count._parameter_valuespec()
    assert all(
        any(tittle == levels for tittle, _ in element._elements())
        for _, element in parameters._elements()
    )


@pytest.fixture
def rulespec():
    for r in kube_node_container_count.rulespec_registry.get_by_group("static/applications"):
        if r.name == "static_checks:kube_node_container_count":
            return r
    assert False, "Should be able to find the rulespec"


@pytest.mark.xfail(reason="`match_type` should be dict")
def test_rulespec_registry_match_type(rulespec):
    assert rulespec.match_type == "dict"


def test_rulespec_registry_parameter_valuespec(rulespec):
    assert rulespec._parameter_valuespec == kube_node_container_count._parameter_valuespec


def test_rulespec_registry_title(rulespec):
    assert rulespec.title == "Kubernetes node containers"
