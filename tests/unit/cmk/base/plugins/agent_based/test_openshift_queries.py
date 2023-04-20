#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import random

import pytest
from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based import openshift_queries as plugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.utils import kube


class OpenShiftEndpointFactory(ModelFactory):
    __model__ = kube.OpenShiftEndpoint


class PrometheusResultFactory(ModelFactory):
    __model__ = kube.PrometheusResult


def random_error_type() -> kube.ResultType:
    return random.choice([type_ for type_ in kube.ResultType if type_ != kube.ResultType.success])


class PrometheusErrorFactory(PrometheusResultFactory):
    type_ = random_error_type


class PrometheusSuccessFactory(PrometheusResultFactory):
    type_ = kube.ResultType.success


def test_check_state_all_queries_succeed() -> None:
    # Assemble
    section = OpenShiftEndpointFactory.build(results=PrometheusSuccessFactory.batch(size=3))

    # Act
    results = list(plugin.check(section))

    # Assert
    assert all(result.state == State.OK for result in results if isinstance(result, Result))


@pytest.mark.parametrize(
    "section",
    [
        OpenShiftEndpointFactory.build(
            results=PrometheusResultFactory.batch(size=3, type_=kube.ResultType.request_exception)
        ),
        OpenShiftEndpointFactory.build(
            results=PrometheusErrorFactory.batch(size=3),
        ),
        OpenShiftEndpointFactory.build(
            results=[PrometheusErrorFactory.build(), PrometheusSuccessFactory.build()]
        ),
    ],
)
def test_check_state_some_query_failed(section: kube.OpenShiftEndpoint) -> None:
    # Act
    results = list(plugin.check(section))

    # Assert
    assert any(result.state != State.OK for result in results if isinstance(result, Result))


def test_check_dont_show_queries_if_they_all_have_the_same_message() -> None:
    # Assemble
    prom_result = PrometheusResultFactory.build()
    section = OpenShiftEndpointFactory.build(results=[prom_result for _ in range(3)])

    # Act
    results = list(plugin.check(section))

    # Assert
    assert all(
        prom_result.query_ not in result.summary and prom_result.query_ not in result.details
        for result in results
        if isinstance(result, Result)
    )


def test_check_url_shown() -> None:
    # Assemble
    section = OpenShiftEndpointFactory.build()

    # Act
    results = list(plugin.check(section))

    # Assert
    assert any(
        section.url in result.summary or section.url in result.details
        for result in results
        if isinstance(result, Result)
    )
