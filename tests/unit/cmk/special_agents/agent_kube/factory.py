#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import itertools
from typing import Iterator

from pydantic_factories import ModelFactory

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api

# General Factories


class MetaDataFactory(ModelFactory):
    __model__ = api.MetaData


# Pod related Factories


class PodMetaDataFactory(ModelFactory):
    __model__ = api.PodMetaData


class PodSpecFactory(ModelFactory):
    __model__ = api.PodSpec


class PodStatusFactory(ModelFactory):
    __model__ = api.PodStatus


class APIPodFactory(ModelFactory):
    __model__ = api.Pod


def pod_phase_generator() -> Iterator[api.Phase]:
    yield from itertools.cycle(api.Phase)


def api_to_agent_pod(pod: api.Pod) -> agent.Pod:
    return agent.Pod(
        uid=pod.uid,
        metadata=pod.metadata,
        status=pod.status,
        spec=pod.spec,
        containers=pod.containers,
        init_containers=pod.init_containers,
    )


# Deployment related Factories


class APIDeploymentFactory(ModelFactory):
    __model__ = api.Deployment


def api_to_agent_deployment(api_deployment: api.Deployment) -> agent.Deployment:
    return agent.Deployment(
        metadata=api_deployment.metadata,
        spec=api_deployment.spec,
        status=api_deployment.status,
    )
