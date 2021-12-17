#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import Literal, Union

from pydantic import BaseModel


class KubernetesError(Exception):
    pass


class Phase(str, enum.Enum):
    RUNNING = "running"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class PodLifeCycle(BaseModel):
    """section: kube_pod_lifecycle_v1"""

    phase: Phase


class ExceptionalResource(str, enum.Enum):
    """
    Kubernetes allows omitting the limits and/or requests field for a container. This enum allows us
    to take this into account, when aggregating containers accross a Kubernetes object.
    """

    unspecified = "unspecified"
    """
    We return this value if there is at least one container, where the limit/request was omitted.
    """
    zero = "zero"
    # Kubernetes allows setting the limit field of a container to zero. According to this issue,
    # https://github.com/kubernetes/kubernetes/issues/86244
    # this means the container with limit 0 has unlimited resources. Our understanding is that this
    # is connected to the behaviour of Docker: Kubernetes passes the Docker runtime the limit value.
    # Docker then assigns all the memory on the host machine. It therefore means that github issues
    # might be inaccurate: If there is a container runtime, which uses the limit differently, then
    # the cluster may behave differently.
    """
    Because limit=0 means unlimited rather than zero, we cannot simply add a limit of 0.
    We return this value if there is at least one container, where the limit field was set to zero.
    """
    zero_unspecified = "zero_unspecified"
    """
    If both of the above conditions apply to a limit, we use this value.
    """


AggregatedLimit = Union[ExceptionalResource, float]
AggregatedRequest = Union[Literal[ExceptionalResource.unspecified], float]


class Resources(BaseModel):
    request: AggregatedRequest
    limit: AggregatedLimit
