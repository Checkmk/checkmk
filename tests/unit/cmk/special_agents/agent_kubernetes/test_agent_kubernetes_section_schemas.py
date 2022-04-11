#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils import kube as check
from cmk.base.plugins.agent_based.utils import kube_resources

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.schemata import section as agent


def test_schemata_did_not_diverge() -> None:
    assert agent.ClusterDetails.schema() == check.ClusterDetails.schema()
    assert agent.ClusterInfo.schema() == check.ClusterInfo.schema()
    assert agent.CollectorProcessingLogs.schema() == check.CollectorProcessingLogs.schema()
    assert agent.CollectorComponentsMetadata.schema() == check.CollectorComponentsMetadata.schema()
    assert agent.ContainerCount.schema() == check.ContainerCount.schema()
    assert api.ContainerRunningState.schema() == check.ContainerRunningState.schema()
    assert api.ContainerTerminatedState.schema() == check.ContainerTerminatedState.schema()
    assert api.ContainerWaitingState.schema() == check.ContainerWaitingState.schema()
    assert agent.DeploymentConditions.schema() == check.DeploymentConditions.schema()
    assert api.KubeletInfo.schema() == check.KubeletInfo.schema()
    assert agent.NamespaceInfo.schema() == check.NamespaceInfo.schema()
    assert agent.NodeCount.schema() == check.NodeCount.schema()
    assert agent.NodeInfo.schema() == check.NodeInfo.schema()
    assert agent.PodCondition.schema() == check.PodCondition.schema()
    assert agent.PodConditions.schema() == check.PodConditions.schema()
    assert agent.PodContainers.schema() == check.PodContainers.schema()
    assert agent.PodResources.schema() == check.PodResources.schema()
    assert agent.PodLifeCycle.schema() == check.PodLifeCycle.schema()
    assert agent.AllocatablePods.schema() == check.AllocatablePods.schema()
    assert agent.Resources.schema() == kube_resources.Resources.schema()
    assert api.StartTime.schema() == check.StartTime.schema()
    assert agent.PodInfo.schema() == check.PodInfo.schema()
    assert agent.UpdateStrategy.schema() == check.UpdateStrategy.schema()
    assert agent.DeploymentReplicas.schema() == check.DeploymentReplicas.schema()
    assert agent.StatefulSetReplicas.schema() == check.StatefulSetReplicas.schema()
    assert agent.DaemonSetReplicas.schema() == check.DaemonSetReplicas.schema()
    assert agent.NodeConditions.schema() == check.NodeConditions.schema()
    assert agent.NodeCustomConditions.schema() == check.NodeCustomConditions.schema()
    assert agent.PerformanceUsage.schema() == check.PerformanceUsage.schema()
    assert agent.DeploymentInfo.schema() == check.DeploymentInfo.schema()
    assert agent.ContainerSpecs.schema() == check.ContainerSpecs.schema()
    assert agent.DaemonSetInfo.schema() == check.DaemonSetInfo.schema()
    assert agent.StatefulSetInfo.schema() == check.StatefulSetInfo.schema()
    assert agent.CollectorDaemons.schema() == check.CollectorDaemons.schema()
