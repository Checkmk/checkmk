#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import (
    Callable,
    Iterable,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

from pydantic import BaseModel

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    Metric,
    render,
    Result,
    State,
)


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


def iterate_resources(
    resources: Resources,
) -> Sequence[Tuple[Literal["request", "limit"], AggregatedLimit]]:
    return [
        ("request", resources.request),
        ("limit", resources.limit),
    ]


class Usage(BaseModel):
    usage: float


Modes = Literal["perc_used", "abs_used"]
Param = Union[Literal["ignore"], Tuple[Modes, Tuple[float, float]]]


class Params(TypedDict):
    request: Param
    limit: Param


DEFAULT_PARAMS = Params(
    request="ignore",
    limit=("perc_used", (80.0, 90.0)),
)


class Levels(NamedTuple):
    warn: float
    crit: float


def scale_to_perc(total: float) -> Callable[[float], float]:
    return lambda x: x * 100.0 / total


def normalize_levels(param: Param, requirement_value: float) -> Optional[Levels]:
    if param == "ignore":
        return None
    if param[0] == "perc_used":
        return Levels(*param[1])
    # param[0] == "abs_used":
    return Levels(*map(scale_to_perc(requirement_value), param[1]))


def check_with_utilization(
    usage: float,
    resource_type: Literal["memory", "cpu"],
    requirement_type: Literal["limit", "request"],
    requirement_value: float,
    param: Param,
    render_func: Callable[[float], str],
) -> Iterable[Union[Metric, Result]]:
    utilization = scale_to_perc(requirement_value)(usage)
    result, metric = check_levels(
        utilization,
        levels_upper=normalize_levels(param, requirement_value),
        metric_name=f"kube_{resource_type}_{requirement_type}_utilization",
        render_func=render.percent,
        boundaries=(0.0, None),
    )
    assert isinstance(result, Result)
    percentage, *warn_crit = result.summary.split()
    yield Result(
        state=result.state,
        summary=" ".join(
            [
                f"{requirement_type.title()} utilization: {percentage} - {render_func(usage)} of {render_func(requirement_value)}"
            ]
            + warn_crit
        ),
    )
    yield metric
    yield Metric(f"kube_{resource_type}_{requirement_type}", requirement_value)


def result_for_exceptional_resource(
    requirement_type: str, requirement_value: ExceptionalResource
) -> Result:
    details_pieces = []
    if requirement_value in (
        ExceptionalResource.unspecified,
        ExceptionalResource.zero_unspecified,
    ):
        details_pieces.append("not specified for at least one container")
    if requirement_value in (ExceptionalResource.zero, ExceptionalResource.zero_unspecified):
        details_pieces.append("set to zero for at least one container")
    return Result(
        state=State.OK,
        summary=f"{requirement_type.title()}: n/a",
        details=f"{requirement_type.title()}: {', '.join(details_pieces)}",
    )
