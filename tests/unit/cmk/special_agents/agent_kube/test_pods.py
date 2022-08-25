#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.unit.cmk.special_agents.agent_kube.factory import (
    APIControllerFactory,
    APIPodFactory,
    MetaDataFactory,
    PodSpecFactory,
    PodStatusFactory,
)

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api, section


def test_pod_conditions_with_no_conditions_present() -> None:
    pod = APIPodFactory.build(status=PodStatusFactory.build(conditions=None))
    assert agent.pod_conditions(pod.status) is None


def test_pod_conditions_with_conditions_present() -> None:
    pod = APIPodFactory.build(
        status=PodStatusFactory.build(
            conditions=[
                api.PodCondition(
                    status=True,
                    type=api.ConditionType.INITIALIZED,
                    custom_type=None,
                    reason="PodCompleted",
                    detail=None,
                    last_transition_time=100,
                ),
                api.PodCondition(
                    status=False,
                    type=api.ConditionType.READY,
                    custom_type=None,
                    reason="PodCompleted",
                    detail=None,
                    last_transition_time=100,
                ),
                api.PodCondition(
                    status=False,
                    type=api.ConditionType.CONTAINERSREADY,
                    custom_type=None,
                    reason="PodCompleted",
                    detail=None,
                    last_transition_time=100,
                ),
                api.PodCondition(
                    status=True,
                    type=api.ConditionType.PODSCHEDULED,
                    custom_type=None,
                    reason=None,
                    detail=None,
                    last_transition_time=100,
                ),
            ]
        )
    )
    section_pod_conditions = agent.pod_conditions(pod.status)

    assert isinstance(section_pod_conditions, section.PodConditions)
    assert section_pod_conditions == section.PodConditions(
        initialized=section.PodCondition(
            status=True, reason="PodCompleted", detail=None, last_transition_time=100
        ),
        ready=section.PodCondition(
            status=False, reason="PodCompleted", detail=None, last_transition_time=100
        ),
        containersready=section.PodCondition(
            status=False, reason="PodCompleted", detail=None, last_transition_time=100
        ),
        scheduled=section.PodCondition(
            status=True, reason=None, detail=None, last_transition_time=100
        ),
    )


def test_pod_container_specs() -> None:
    pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[]))
    section_pod_container_specs = agent.pod_container_specs(pod.spec)

    assert section_pod_container_specs == section.ContainerSpecs(containers={})


def test_pod_init_container_specs() -> None:
    pod = APIPodFactory.build(
        spec=PodSpecFactory.build(
            init_containers=[
                api.ContainerSpec(
                    resources=api.ContainerResources(
                        limits=api.ResourcesRequirements(memory=2, cpu=10),
                        requests=api.ResourcesRequirements(memory=None, cpu=1),
                    ),
                    name="init_container",
                    image_pull_policy="Never",
                )
            ]
        )
    )
    section_pod_init_container_specs = agent.pod_init_container_specs(pod.spec)

    assert isinstance(section_pod_init_container_specs, section.ContainerSpecs)
    assert section_pod_init_container_specs == section.ContainerSpecs(
        containers={"init_container": section.ContainerSpec(image_pull_policy="Never")}
    )


def test_pod_start_time_with_no_start_time_present() -> None:
    pod = APIPodFactory.build(status=PodStatusFactory.build(start_time=None))

    assert agent.pod_start_time(pod.status) is None


def test_pod_start_time_with_start_time_present() -> None:
    pod = APIPodFactory.build(status=PodStatusFactory.build(start_time=100.0))
    section_pod_start_time = agent.pod_start_time(pod.status)

    assert isinstance(section_pod_start_time, section.StartTime)
    assert section_pod_start_time == section.StartTime(start_time=100.0)


def test_pod_lifecycle_phase() -> None:
    pod = APIPodFactory.build(status=PodStatusFactory.build(phase=api.Phase.RUNNING))
    section_pod_lifecycle_phase = agent.pod_lifecycle_phase(pod.status)

    assert isinstance(section_pod_lifecycle_phase, section.PodLifeCycle)
    assert section_pod_lifecycle_phase == section.PodLifeCycle(phase=api.Phase.RUNNING)


def test_pod_info() -> None:
    pod = APIPodFactory.build(
        metadata=MetaDataFactory.build(
            name="pod-name",
            annotations={},
            creation_timestamp=100.0,
            labels={},
            namespace="namespace-name",
        ),
        spec=PodSpecFactory.build(
            node="node-name",
            host_network=None,
            dns_policy="ClusterFirst",
            restart_policy="Always",
        ),
        status=PodStatusFactory.build(
            host_ip="127.0.0.1",
            pod_ip="11.1.1.1",
            qos_class="besteffort",
        ),
        controllers=[
            APIControllerFactory.build(
                type_=api.ControllerType.cronjob, name="cronjob-name", namespace="namespace-name"
            )
        ],
        uid="pod-uid",
    )
    section_pod_info = agent.pod_info(
        pod,
        cluster_name="cluster-name",
        kubernetes_cluster_hostname="host",
        annotation_key_pattern="import_all",
    )

    assert isinstance(section_pod_info, section.PodInfo)
    assert section_pod_info == section.PodInfo(
        name="pod-name",
        namespace="namespace-name",
        creation_timestamp=100.0,
        annotations={},
        labels={},
        node="node-name",
        host_ip="127.0.0.1",
        pod_ip="11.1.1.1",
        qos_class="besteffort",
        cluster_name="cluster-name",
        host_network=None,
        dns_policy="ClusterFirst",
        restart_policy="Always",
        controllers=[
            section.Controller(
                type_=section.ControllerType.cronjob, name="namespace-name_cronjob-name"
            )
        ],
        cluster="cluster-name",
        uid="pod-uid",
        kubernetes_cluster_hostname="host",
    )
