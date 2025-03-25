#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to help generate pydantic based Kubernetes models

Notice (for polyfactory):
    For models which make use of validator such as api.StorageRequirement, the build function will
    first generate the field value before passing it through the validator function. This will in
    some cases raise an error.

    You should make use of the factory_use_construct option to bypass the validator function. This
    option is tied to the model so won't be applied to nested models. See how APIDataFactory
    resolves this with persistent_volume_claims.
"""

import itertools
import random
import typing
from collections.abc import Iterator, Sequence

import pydantic
from polyfactory import Use
from polyfactory.factories.dataclass_factory import DataclassFactory
from polyfactory.factories.pydantic_factory import ModelFactory

import cmk.plugins.kube.agent_handlers.common
from cmk.plugins.kube import common, performance, prometheus_api
from cmk.plugins.kube.api_server import APIData
from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.special_agents import agent_kube as agent

T = typing.TypeVar("T", bound=pydantic.BaseModel)


class Batch(typing.Protocol[T]):
    def __call__(self, size: int) -> list[T]: ...


def randomize_size(batch: Batch[T]) -> typing.Callable[[], list[T]]:
    def use() -> list[T]:
        return batch(size=random.choice([0, 1, 2, 4, 8]))

    return use


# Container related Factories
class ContainerRunningStateFactory(ModelFactory):
    __model__ = api.ContainerRunningState


class ContainerWaitingStateFactory(ModelFactory):
    __model__ = api.ContainerWaitingState


class ContainerTerminatedStateFactory(ModelFactory):
    __model__ = api.ContainerTerminatedState


def create_container_state(state: api.ContainerStateType) -> api.ContainerState:
    state_factory = {
        api.ContainerStateType.running: ContainerRunningStateFactory.build,
        api.ContainerStateType.waiting: ContainerWaitingStateFactory.build,
        api.ContainerStateType.terminated: ContainerTerminatedStateFactory.build,
    }[state]
    return state_factory()


class ContainerStatusFactory(ModelFactory):
    __model__ = api.ContainerStatus


class ContainerSpecFactory(ModelFactory):
    __model__ = api.ContainerSpec


class ContainerResourcesFactory(ModelFactory):
    __model__ = api.ContainerResources


# General Factories


class MetaDataFactory(ModelFactory[api.MetaData]):
    __model__ = api.MetaData


class MetaDataNoNamespaceFactory(ModelFactory[api.MetaDataNoNamespace]):
    __model__ = api.MetaDataNoNamespace


# Pod related Factories
class VolumePersistentVolumeClaimSourceFactory(ModelFactory):
    __model__ = api.VolumePersistentVolumeClaimSource


class PodVolumeFactory(ModelFactory):
    __model__ = api.Volume


class PodSpecFactory(ModelFactory):
    __model__ = api.PodSpec


class PodStatusFactory(ModelFactory):
    __model__ = api.PodStatus


class APIPodFactory(ModelFactory):
    __model__ = api.Pod

    metadata = Use(MetaDataFactory.build, factory_use_construct=True)


class APIControllerFactory(ModelFactory):
    __model__ = api.Controller


def pod_phase_generator() -> Iterator[api.Phase]:
    yield from itertools.cycle(api.Phase)


# Deployment related Factories


class DeploymentStatusFactory(ModelFactory):
    __model__ = api.DeploymentStatus


class APIDeploymentFactory(ModelFactory):
    __model__ = api.Deployment

    metadata = Use(MetaDataFactory.build, factory_use_construct=True)


def api_to_agent_deployment(
    api_deployment: api.Deployment, pods: Sequence[api.Pod] = ()
) -> cmk.plugins.kube.agent_handlers.common.Deployment:
    return cmk.plugins.kube.agent_handlers.common.Deployment(
        metadata=api_deployment.metadata,
        spec=api_deployment.spec,
        status=api_deployment.status,
        pods=pods,
    )


# DaemonSet related Factories


class APIDaemonSetFactory(ModelFactory):
    __model__ = api.DaemonSet

    metadata = Use(MetaDataFactory.build, factory_use_construct=True)


def api_to_agent_daemonset(
    api_daemonset: api.DaemonSet, pods: Sequence[api.Pod] = ()
) -> cmk.plugins.kube.agent_handlers.common.DaemonSet:
    return cmk.plugins.kube.agent_handlers.common.DaemonSet(
        metadata=api_daemonset.metadata,
        spec=api_daemonset.spec,
        status=api_daemonset.status,
        pods=pods,
    )


# StatefulSet related Factories


class APIStatefulSetFactory(ModelFactory):
    __model__ = api.StatefulSet

    metadata = Use(MetaDataFactory.build, factory_use_construct=True)


def api_to_agent_statefulset(
    api_statefulset: api.StatefulSet, pods: Sequence[api.Pod] = ()
) -> cmk.plugins.kube.agent_handlers.common.StatefulSet:
    return cmk.plugins.kube.agent_handlers.common.StatefulSet(
        metadata=api_statefulset.metadata,
        spec=api_statefulset.spec,
        status=api_statefulset.status,
        pods=pods,
    )


# Namespace & Resource Quota related Factories


class NamespaceMetaDataFactory(ModelFactory):
    __model__ = api.NamespaceMetaData


class APIResourceQuotaFactory(ModelFactory):
    __model__ = api.ResourceQuota

    metadata = Use(MetaDataFactory.build, factory_use_construct=True)


class APINamespaceFactory(ModelFactory):
    __model__ = api.Namespace

    metadata = Use(NamespaceMetaDataFactory.build, factory_use_construct=True)


# Performance related Factories


class PerformanceSampleFactory(ModelFactory):
    __model__ = performance.PerformanceSample


class MemorySampleFactory(ModelFactory):
    __model__ = performance.MemorySample
    metric_value_string = Use(ModelFactory.__random__.choice, ["1.0", "10.0", "2000.0"])


class CPURateSampleFactory(ModelFactory):
    __model__ = performance.CPURateSample


class CPUSampleFactory(ModelFactory):
    __model__ = performance.CPUSample
    metric_value_string = Use(ModelFactory.__random__.choice, ["1.0", "10.0", "2000.0"])


class IdentifiableSampleFactory(ModelFactory):
    __model__ = common.IdentifiableSample


# PersistentVolumeClaim related Factories


class StorageRequirementFactory(ModelFactory):
    __model__ = api.StorageRequirement


class StorageResourceRequirementsFactory(ModelFactory):
    __model__ = api.StorageResourceRequirements

    limits = Use(StorageRequirementFactory.build, factory_use_construct=True)
    requests = Use(StorageRequirementFactory.build, factory_use_construct=True)


class PersistentVolumeSpecFactory(ModelFactory):
    __model__ = api.PersistentVolumeClaimSpec

    resources = StorageResourceRequirementsFactory.build


class PersistentVolumeClaimStatusFactory(ModelFactory):
    __model__ = api.PersistentVolumeClaimStatus

    capacity = Use(StorageRequirementFactory.build, factory_use_construct=True)


class PersistentVolumeClaimFactory(ModelFactory):
    __model__ = api.PersistentVolumeClaim

    spec = PersistentVolumeSpecFactory.build
    status = PersistentVolumeClaimStatusFactory.build
    metadata = Use(MetaDataFactory.build, factory_use_construct=True)


class PersistentVolumeFactory(ModelFactory):
    __model__ = api.PersistentVolume

    metadata = Use(MetaDataFactory.build, factory_use_construct=True)


# Node related Factories


class NodeMetaDataFactory(ModelFactory):
    __model__ = api.NodeMetaData


class NodeResourcesFactory(ModelFactory):
    __model__ = api.NodeResources


class NodeConditionFactory(ModelFactory):
    __model__ = api.NodeCondition


class NodeStatusFactory(ModelFactory):
    __model__ = api.NodeStatus

    allocatable = Use(NodeResourcesFactory.build, factory_use_construct=True)
    capacity = Use(NodeResourcesFactory.build, factory_use_construct=True)


class APINodeFactory(ModelFactory):
    __model__ = api.Node

    status = NodeStatusFactory.build
    metadata = Use(NodeMetaDataFactory.build, factory_use_construct=True)


def api_to_agent_node(
    node: api.Node, pods: Sequence[api.Pod] = ()
) -> cmk.plugins.kube.agent_handlers.common.Node:
    return cmk.plugins.kube.agent_handlers.common.Node(
        metadata=node.metadata,
        status=node.status,
        kubelet_health=node.kubelet_health,
        pods=pods,
    )


# CronJob


class CronJobStatusFactory(ModelFactory):
    __model__ = api.CronJobStatus


class JobStatusFactory(ModelFactory):
    __model__ = api.JobStatus


class APIJobFactory(ModelFactory):
    __model__ = api.Job

    metadata = Use(MetaDataFactory.build, factory_use_construct=True)


class APICronJobFactory(ModelFactory):
    __model__ = api.CronJob

    metadata = Use(MetaDataFactory.build, factory_use_construct=True)


# Prometheus API


class ResponseSuccessFactory(ModelFactory):
    __model__ = prometheus_api.ResponseSuccess


class ResponseErrorFactory(ModelFactory):
    __model__ = prometheus_api.ResponseError


class VectorFactory(ModelFactory):
    __model__ = prometheus_api.Vector


class SampleFactory(ModelFactory):
    __model__ = prometheus_api.Sample


# Cluster related Factories


class APIDataFactory(DataclassFactory):
    __model__ = APIData

    persistent_volume_claims = randomize_size(PersistentVolumeClaimFactory.batch)
    persistent_volumes = randomize_size(PersistentVolumeFactory.batch)
    nodes = randomize_size(APINodeFactory.batch)
    cron_jobs = randomize_size(APICronJobFactory.batch)
    deployments = randomize_size(APIDeploymentFactory.batch)
    daemonsets = randomize_size(APIDaemonSetFactory.batch)
    jobs = randomize_size(APIJobFactory.batch)
    statefulsets = randomize_size(APIStatefulSetFactory.batch)
    namespaces = randomize_size(APINamespaceFactory.batch)
    pods = randomize_size(APIPodFactory.batch)
    resource_quotas = randomize_size(APIResourceQuotaFactory.batch)


class ClusterDetailsFactory(ModelFactory):
    __model__ = api.ClusterDetails


def composed_entities_builder(
    *,
    cluster_details: api.ClusterDetails | None = None,
    daemonsets: Sequence[api.DaemonSet] = (),
    statefulsets: Sequence[api.StatefulSet] = (),
    deployments: Sequence[api.Deployment] = (),
    pods: Sequence[api.Pod] = (),
    nodes: Sequence[api.Node] = (),
) -> agent.ComposedEntities:
    controllers: Iterator[api.DaemonSet | api.StatefulSet | api.Deployment] = itertools.chain(
        daemonsets, statefulsets, deployments
    )
    if not pods:
        pods = [
            APIPodFactory.build(uid=uid) for controller in controllers for uid in controller.pods
        ]
    return agent.ComposedEntities.from_api_resources(
        excluded_node_roles=(),
        api_data=APIDataFactory.build(
            cluster_details=cluster_details or ClusterDetailsFactory.build(),
            nodes=nodes,
            statefulsets=statefulsets,
            deployments=deployments,
            daemonsets=daemonsets,
            pods=pods,
        ),
    )


APIDataFactory.build()
