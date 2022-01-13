#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import json
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
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, StringTable


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


def parse_resources(string_table: StringTable) -> Resources:
    """Parses limit and request values into Resources
    >>> parse_resources([['{"request": 23120704.0, "limit": 28120704.0}']])
    Resources(request=23120704.0, limit=28120704.0)
    >>> parse_resources([['{"request": "unspecified", "limit": "unspecified"}']])
    Resources(request=<ExceptionalResource.unspecified: 'unspecified'>, limit=<ExceptionalResource.unspecified: 'unspecified'>)
    >>> parse_resources([['{"request": 0.0, "limit": "zero"}']])
    Resources(request=0.0, limit=<ExceptionalResource.zero: 'zero'>)
    """
    return Resources(**json.loads(string_table[0][0]))


class Usage(BaseModel):
    usage: float


Modes = Literal["perc_used", "abs_used"]
Param = Union[Literal["ignore"], Tuple[Modes, Tuple[float, float]]]


class Params(TypedDict):
    request: Param
    limit: Param


DEFAULT_PARAMS = Params(
    request="ignore",
    limit="ignore",
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


def check_resource(
    params: Params,
    usage: Optional[Usage],
    resources: Optional[Resources],
    resource_type: Literal["memory", "cpu"],
    render_func: Callable[[float], str],
) -> CheckResult:
    if usage is not None:
        total_usage = usage.usage
        yield from check_levels(
            total_usage,
            label="Usage",
            levels_upper=None,
            metric_name=f"kube_{resource_type}_usage",
            render_func=render_func,
            boundaries=(0.0, None),
        )

    if resources is not None:
        for requirement_name, requirement in iterate_resources(resources):
            if isinstance(requirement, float) and requirement != 0.0 and usage is not None:
                param = params[requirement_name]
                yield from check_with_utilization(
                    total_usage,
                    resource_type,
                    requirement_name,
                    requirement,
                    param,
                    render_func,
                )
            elif isinstance(requirement, ExceptionalResource):
                yield result_for_exceptional_resource(requirement_name, requirement)
            else:  # configured resource with no usage
                yield from check_levels(
                    requirement,
                    label=requirement_name.title(),
                    metric_name=f"kube_{resource_type}_{requirement_name}",
                    render_func=render_func,
                    boundaries=(0.0, None),
                )
