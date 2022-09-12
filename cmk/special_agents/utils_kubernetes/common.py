#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Module for definitions and functions which are used by both the special_agent/agent_kube and
the utils_kubernetes/performance
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping, NewType, Sequence

LOGGER = logging.getLogger()
RawMetrics = Mapping[str, str]
PodLookupName = NewType("PodLookupName", str)

SectionName = NewType("SectionName", str)
SectionJson = NewType("SectionJson", str)


@dataclass
class Piggyback:
    piggyback: str
    pod_names: Sequence[PodLookupName]


@dataclass
class NamespacePiggy(Piggyback):
    resource_quota_pod_names: Sequence[PodLookupName]


@dataclass
class PodsToHost:
    piggybacks: Sequence[Piggyback]
    cluster_pods: Sequence[PodLookupName]
    namespace_piggies: Sequence[NamespacePiggy]


def lookup_name(namespace: str, name: str) -> PodLookupName:
    """Parse the pod lookup name

    This function parses an identifier which is used to match the pod based on the
    performance data to the associating pod based on the Kubernetes API data

    The namespace & pod name combination is unique across the cluster and is used instead of the pod
    uid due to a cAdvisor bug. This bug causes it to return the container config hash value
    (kubernetes.io/config.hash) as the pod uid for system containers and consequently differs to the
    uid reported by the Kubernetes API.
    """
    return PodLookupName(f"{namespace}_{name}")
