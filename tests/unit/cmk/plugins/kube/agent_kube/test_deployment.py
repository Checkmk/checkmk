#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest_mock
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.plugins.kube.agent_handlers import deployment_handler, pod_handler
from cmk.plugins.kube.agent_handlers.common import AnnotationNonPatternOption, CheckmkHostSettings
from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.special_agents import agent_kube as agent

from tests.unit.cmk.plugins.kube.agent_kube.factory import (
    api_to_agent_deployment,
    APIControllerFactory,
    APIDeploymentFactory,
    APIPodFactory,
    DeploymentStatusFactory,
)


class DeploymentConditionFactory(ModelFactory):
    __model__ = api.DeploymentCondition


def deployments_api_sections() -> set[str]:
    return {
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_deployment_info_v1",
        "kube_deployment_conditions_v1",
        "kube_cpu_resources_v1",
        "kube_update_strategy_v1",
        "kube_deployment_replicas_v1",
        "kube_controller_spec_v1",
    }


def test_pod_deployment_controller_name() -> None:
    pod = APIPodFactory.build(controllers=[APIControllerFactory.build(name="hi", namespace="bye")])
    pod_info = pod_handler._info(
        pod,
        "cluster",
        "host",
        AnnotationNonPatternOption.ignore_all,
    )
    assert len(pod_info.controllers) == 1
    assert pod_info.controllers[0].name == "hi"


def test_deployment_conditions() -> None:
    api_deployment_status = DeploymentStatusFactory.build(
        conditions={
            condition: DeploymentConditionFactory.build()
            for condition in ["available", "progressing", "replicafailure"]
        }
    )
    conditions = deployment_handler._conditions(api_deployment_status)
    assert conditions is not None
    assert all(condition_details is not None for _, condition_details in conditions)


def test_write_deployments_api_sections_registers_sections_to_be_written(
    mocker: pytest_mock.MockFixture,
) -> None:
    write_sections_mock = mocker.patch("cmk.plugins.kube.common.write_sections")
    deployment = api_to_agent_deployment(APIDeploymentFactory.build(), pods=[APIPodFactory.build()])
    deployment_sections = deployment_handler.create_api_sections(
        deployment,
        CheckmkHostSettings(
            cluster_name="cluster",
            kubernetes_cluster_hostname="host",
            annotation_key_pattern=AnnotationNonPatternOption.ignore_all,
        ),
        "deployment",
    )
    # Too much monkeypatching/mocking, the typing error isn't worth fixing.
    agent.common.write_sections(deployment_sections)  # type: ignore[attr-defined]
    assert {
        section.section_name for section in write_sections_mock.call_args[0][0]
    } == deployments_api_sections()
