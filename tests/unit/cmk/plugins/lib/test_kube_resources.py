#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Result, State
from cmk.plugins.kube.schemata.section import AllocatableResource, Resources
from cmk.plugins.lib import kube_resources


class ResourcesFactory(ModelFactory):
    __model__ = Resources


class AllocatableResourceFactory(ModelFactory):
    __model__ = AllocatableResource


def test_requirements_for_object_has_request_limit_ordered_as_per_kubernetes_convention() -> None:
    resources = ResourcesFactory.build()
    expected = ["request", "limit"]
    actual = [t for t, _, _ in kube_resources.requirements_for_object(resources, None)]
    assert actual == expected


def test_requirements_for_object_has_allocatable_after_limit() -> None:
    resources = ResourcesFactory.build()
    allocatable = AllocatableResourceFactory.build()
    expected = ["request", "limit", "allocatable"]
    actual = [t for t, _, _ in kube_resources.requirements_for_object(resources, allocatable)]
    assert actual == expected


def test_check_with_utilization_lower_request_levels() -> None:
    # Act
    check_results = list(
        kube_resources.check_with_utilization(
            1.0,
            "memory",
            "request",
            None,
            2.0,
            kube_resources.Params(
                usage="no_levels",
                request="no_levels",
                request_lower=("levels", (80.0, 90.0)),
                limit="no_levels",
                cluster="no_levels",
                node="no_levels",
            ),
            str,
        )
    )
    # Assert
    assert any(
        isinstance(result, Result) and result.state == State.CRIT for result in check_results
    )
