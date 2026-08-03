#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import contextlib
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.aws.lib import discover_aws_generic, parse_aws

Section = Mapping[str, Mapping[str, Any]]


def parse_aws_s3(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, Any]] = {}
    for row in parse_aws(string_table):
        bucket = parsed.setdefault(row["Label"], {})
        with contextlib.suppress(KeyError):
            bucket["LocationConstraint"] = row["LocationConstraint"]
        with contextlib.suppress(KeyError):
            bucket["Tagging"] = row["Tagging"]
        storage_key, size_key = row["Id"].split("_")[-2:]
        inst = bucket.setdefault(size_key, {})
        with contextlib.suppress(IndexError, ValueError):
            # if the entry exists, the first value is the numerical value of the metric and the
            # second one is the period, which is None here since these are not statistics of type
            # "Sum"
            inst.setdefault(storage_key, row["Values"][0][0])
    return parsed


def discover_aws_s3(section: Section) -> DiscoveryResult:
    yield from discover_aws_generic(section, ["BucketSizeBytes", "NumberOfObjects"])


def check_aws_s3_objects(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (metrics := section.get(item)):
        return

    bucket_sizes = metrics["BucketSizeBytes"]
    storage_infos = [
        f"{storage_type}: {render.bytes(value)}" for storage_type, value in bucket_sizes.items()
    ]
    sum_size = sum(bucket_sizes.values())
    yield from check_levels_v1(
        sum_size,
        metric_name="aws_bucket_size",
        levels_upper=params.get("bucket_size_levels", (None, None)),
        render_func=render.bytes,
        label="Bucket size",
    )
    if storage_infos:
        yield Result(state=State.OK, summary=", ".join(storage_infos))

    num_objects = sum(metrics["NumberOfObjects"].values())
    yield Result(state=State.OK, summary=f"Number of objects: {int(num_objects)}")
    yield Metric("aws_num_objects", num_objects)

    if location := metrics.get("LocationConstraint"):
        yield Result(state=State.OK, summary=f"Location: {location}")

    tag_infos = [f"{tag['Key']}: {tag['Value']}" for tag in metrics.get("Tagging", {})]
    if tag_infos:
        yield Result(state=State.OK, summary=f"[Tags] {', '.join(tag_infos)}")


agent_section_aws_s3 = AgentSection(
    name="aws_s3",
    parse_function=parse_aws_s3,
)


check_plugin_aws_s3 = CheckPlugin(
    name="aws_s3",
    service_name="AWS/S3 Objects %s",
    discovery_function=discover_aws_s3,
    check_function=check_aws_s3_objects,
    check_ruleset_name="aws_s3_buckets_objects",
    check_default_parameters={},
)


def discover_aws_s3_summary(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_aws_s3_summary(params: Mapping[str, Any], section: Section) -> CheckResult:
    sum_size = 0
    largest_bucket = None
    largest_bucket_size = 0
    for bucket_name, bucket in section.items():
        bucket_size = sum(bucket["BucketSizeBytes"].values())
        sum_size += bucket_size
        if bucket_size >= largest_bucket_size:
            largest_bucket = bucket_name
            largest_bucket_size = bucket_size
    yield from check_levels_v1(
        sum_size,
        metric_name="aws_bucket_size",
        levels_upper=params.get("bucket_size_levels", (None, None)),
        render_func=render.bytes,
        label="Total size",
    )

    if largest_bucket:
        yield Result(
            state=State.OK,
            summary=f"Largest bucket: {largest_bucket} ({render.bytes(largest_bucket_size)})",
        )
        yield Metric("aws_largest_bucket_size", largest_bucket_size)


check_plugin_aws_s3_summary = CheckPlugin(
    name="aws_s3_summary",
    service_name="AWS/S3 Summary",
    sections=["aws_s3"],
    discovery_function=discover_aws_s3_summary,
    check_function=check_aws_s3_summary,
    check_ruleset_name="aws_s3_buckets",
    check_default_parameters={},
)
