#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, MutableMapping
from typing import Any, cast, Literal, TypedDict

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import CheckResult, Metric, render, Result
from cmk.plugins.kube.schemata.section import (
    AllocatableResource,
    HardResourceRequirement,
    PerformanceUsage,
    Resources,
)

ResourceType = Literal["memory", "cpu"]
RequirementType = Literal["request", "limit", "allocatable"]
AllocatableKubernetesObject = Literal["cluster", "node"]


# TODO: Resources is a bad name, this should be changed to something like Requirements. When
# choosing a name, other section BaseModel names like AllocatableResource and PerformanceUsage
# be taken into account
def parse_performance_usage(string_table: StringTable) -> PerformanceUsage:
    """Parses usage value for CPU and memory into PerformanceUsage

    >>> parse_performance_usage([['{"resource": {"type_": "memory", "usage": 18120704.0}}']])
    PerformanceUsage(resource=Memory(type_='memory', usage=18120704.0))
    >>> parse_performance_usage([['{"resource": {"type_": "cpu", "usage": 0.9}}']])
    PerformanceUsage(resource=Cpu(type_='cpu', usage=0.9))
    """
    return PerformanceUsage.model_validate_json(string_table[0][0])


def count_overview(resources: Resources, requirement: RequirementType) -> str:
    ignored = (
        resources.count_unspecified_requests
        if requirement == "request"
        else resources.count_unspecified_limits + resources.count_zeroed_limits
    )
    return (
        f"{resources.count_total - ignored}/{resources.count_total} containers with {requirement}s"
    )


def parse_resources(string_table: StringTable) -> Resources:
    """Parses limit and request values into Resources
    >>> parse_resources([['{"request": 209715200.0,'
    ... '"limit": 104857600.0,'
    ... '"count_unspecified_requests": 0,'
    ... '"count_unspecified_limits": 0,'
    ... '"count_zeroed_limits": 1,'
    ... '"count_total": 1}']])
    Resources(request=209715200.0, limit=104857600.0, count_unspecified_requests=0, count_unspecified_limits=0, count_zeroed_limits=1, count_total=1)
    """
    return Resources.model_validate_json(string_table[0][0])


def parse_hard_requirements(string_table: StringTable) -> HardResourceRequirement:
    return HardResourceRequirement.model_validate_json(string_table[0][0])


def parse_allocatable_resource(string_table: StringTable) -> AllocatableResource:
    """Parses allocatable value into AllocatableResource
    >>> parse_allocatable_resource([['{"context": "node", "value": 23120704.0}']])
    AllocatableResource(context='node', value=23120704.0)
    >>> parse_allocatable_resource([['{"context": "cluster", "value": 6.0}']])
    AllocatableResource(context='cluster', value=6.0)
    """
    return AllocatableResource.model_validate_json(string_table[0][0])


Param = Literal["no_levels"] | tuple[Literal["levels"], tuple[float, float]]


class Params(TypedDict, total=False):
    usage: Param
    request: Param
    request_lower: Param
    limit: Param
    cluster: Param
    node: Param


DEFAULT_PARAMS = Params(
    usage="no_levels",
    request="no_levels",
    request_lower="no_levels",
    limit="no_levels",
    cluster="no_levels",
    node="no_levels",
)


RESOURCE_QUOTA_DEFAULT_PARAMS = Params(
    usage="no_levels",
    request="no_levels",
    request_lower="no_levels",
    limit="no_levels",
)


utilization_title: Mapping[RequirementType | AllocatableKubernetesObject, str] = {
    "request": "Requests utilization",
    "limit": "Limits utilization",
    "node": "Node utilization",
    "cluster": "Cluster utilization",
}

absolute_title: Mapping[RequirementType | AllocatableKubernetesObject, str] = {
    "request": "Requests",
    "limit": "Limits",
    "allocatable": "Allocatable",
}


def cpu_render_func(x: float) -> str:
    return f"{x:0.3f}"


def _get_request_lower_levels(
    params: Params, requirement_type: RequirementType
) -> tuple[float, float] | None:
    request_lower = params.get("request_lower", "no_levels")
    if request_lower == "no_levels" or requirement_type != "request":
        return None
    return request_lower[1]


def check_with_utilization(
    usage: float,
    resource_type: ResourceType,
    requirement_type: RequirementType,
    kubernetes_object: AllocatableKubernetesObject | None,
    requirement_value: float,
    params: Params,
    render_func: Callable[[float], str],
) -> Iterable[Metric | Result]:
    utilization = usage * 100.0 / requirement_value
    if kubernetes_object is None:
        metric_name = f"kube_{resource_type}_{requirement_type}_utilization"
        assert requirement_type != "allocatable"
        param = params[requirement_type]
        title = utilization_title[requirement_type]
    else:
        metric_name = f"kube_{resource_type}_{kubernetes_object}_{requirement_type}_utilization"
        param = params[kubernetes_object]
        title = utilization_title[kubernetes_object]
    result, metric = check_levels_v1(
        utilization,
        levels_upper=param[1] if param != "no_levels" else None,
        levels_lower=_get_request_lower_levels(params, requirement_type),
        metric_name=metric_name,
        render_func=render.percent,
        boundaries=(0.0, None),
    )
    assert isinstance(result, Result)
    percentage, *warn_crit = result.summary.split()
    yield Result(
        state=result.state,
        summary=" ".join(
            [f"{title}: {percentage} - {render_func(usage)} of {render_func(requirement_value)}"]
            + warn_crit
        ),
    )
    yield metric


def requirements_for_object(
    resources: Resources, allocatable_resource: AllocatableResource | None
) -> Iterable[tuple[RequirementType, AllocatableKubernetesObject | None, float]]:
    yield "request", None, resources.request
    yield "limit", None, resources.limit
    if allocatable_resource is not None:
        yield "allocatable", allocatable_resource.context, allocatable_resource.value


def check_resource(
    params: Params,
    resource_usage: PerformanceUsage | None,
    resources: Resources,
    allocatable_resource: AllocatableResource | None,
    resource_type: ResourceType,
    render_func: Callable[[float], str],
) -> CheckResult:
    if resource_usage is not None:
        usage = resource_usage.resource.usage
        yield from check_levels_v1(
            usage,
            label="Usage",
            levels_upper=params["usage"][1] if params["usage"] != "no_levels" else None,
            metric_name=f"kube_{resource_type}_usage",
            render_func=render_func,
            boundaries=(0.0, None),
        )
    for requirement_type, kubernetes_object, requirement in requirements_for_object(
        resources, allocatable_resource
    ):
        if requirement != 0.0 and resource_usage is not None:
            result, metric = check_with_utilization(
                usage,
                resource_type,
                requirement_type,
                kubernetes_object,
                requirement,
                params,
                render_func,
            )
            yield Metric(f"kube_{resource_type}_{requirement_type}", requirement)
        else:  # requirements with no usage
            result, metric = check_levels_v1(
                requirement,
                label=absolute_title[requirement_type],
                metric_name=f"kube_{resource_type}_{requirement_type}",
                render_func=render_func,
                boundaries=(0.0, None),
            )
        assert isinstance(result, Result)
        summary = result.summary
        if requirement_type in ["request", "limit"]:
            summary = f"{result.summary} ({count_overview(resources, requirement_type)})"
        yield Result(state=result.state, summary=summary)
        yield metric


def check_resource_quota_resource(
    params: Params,
    resource_usage: PerformanceUsage | None,
    hard_requirement: HardResourceRequirement | None,
    resource_type: ResourceType,
    render_func: Callable[[float], str],
) -> CheckResult:
    """Check result for resource quota usage & requirement

    While the general picture is similar to check_resource, there is one key difference:

    * for resources in check_resource, the resource section contains an aggregation of the request
    and limit values of the underlying containers. In resource quota, the configured hard spec
    value is taken instead (aggregated configured values vs single configured value)

    -> while the API data is mandatory for check_resource, it is optional for resource quota and the
    service is allowed to only display the performance usage value
    """
    usage = resource_usage.resource.usage if resource_usage is not None else None
    if usage is not None:
        yield from check_levels_v1(
            usage,
            label="Usage",
            levels_upper=params["usage"][1] if params["usage"] != "no_levels" else None,
            metric_name=f"kube_{resource_type}_usage",
            render_func=render_func,
            boundaries=(0.0, None),
        )

    if hard_requirement is None:
        return

    for requirement_type, requirement_value in [
        ("request", hard_requirement.request),
        ("limit", hard_requirement.limit),
    ]:
        if requirement_value is None:
            # user has not configured a value for this requirement
            continue

        requirement_type = cast(RequirementType, requirement_type)
        if requirement_value != 0.0 and usage is not None:
            yield from check_with_utilization(
                usage,
                resource_type=resource_type,
                requirement_type=requirement_type,
                kubernetes_object=None,
                requirement_value=requirement_value,
                params=params,
                render_func=render_func,
            )
        else:  # requirements with no usage
            yield from check_levels_v1(
                requirement_value,
                label=absolute_title[requirement_type],
                metric_name=f"kube_{resource_type}_{requirement_type}",
                render_func=render_func,
                boundaries=(0.0, None),
            )


def performance_cpu(
    section_kube_performance_cpu: PerformanceUsage | None,
    current_timestamp: float,
    host_value_store: MutableMapping[str, Any],
    value_store_key: Literal["cpu_usage", "resource_quota_cpu_usage"],
) -> PerformanceUsage | None:
    """Persists the performance usage and uses the stored value for a certain period of time if
    no new data is available.
    """
    if section_kube_performance_cpu is not None:
        host_value_store[value_store_key] = (
            current_timestamp,
            section_kube_performance_cpu.model_dump_json(),
        )
        return section_kube_performance_cpu

    if (timestamped_usage := host_value_store.get(value_store_key)) is not None:
        timestamp, usage = timestamped_usage
        if current_timestamp - timestamp <= 60:
            return PerformanceUsage.model_validate_json(usage)
        # remove the stored value if older than 60 seconds
        host_value_store.pop(value_store_key)

    return None
