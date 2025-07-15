#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.base.check_legacy_includes.aws import inventory_aws_generic, parse_aws

check_info = {}

Section = Mapping[str, Mapping]


def parse_aws_s3(string_table):
    parsed: dict[str, dict] = {}
    for row in parse_aws(string_table):
        bucket = parsed.setdefault(row["Label"], {})
        try:
            bucket["LocationConstraint"] = row["LocationConstraint"]
        except KeyError:
            pass
        try:
            bucket["Tagging"] = row["Tagging"]
        except KeyError:
            pass
        storage_key, size_key = row["Id"].split("_")[-2:]
        inst = bucket.setdefault(size_key, {})
        try:
            # if the entry exists, the first value is the numerical value of the metric and the
            # second one is the period, which is None here since these are not statistics of type
            # "Sum"
            inst.setdefault(storage_key, row["Values"][0][0])
        except (IndexError, ValueError):
            pass
    return parsed


#   .--S3 objects----------------------------------------------------------.
#   |            ____ _____         _     _           _                    |
#   |           / ___|___ /    ___ | |__ (_) ___  ___| |_ ___              |
#   |           \___ \ |_ \   / _ \| '_ \| |/ _ \/ __| __/ __|             |
#   |            ___) |__) | | (_) | |_) | |  __/ (__| |_\__ \             |
#   |           |____/____/   \___/|_.__// |\___|\___|\__|___/             |
#   |                                  |__/                                |
#   '----------------------------------------------------------------------'


def check_aws_s3_objects(item, params, parsed):
    if not (metrics := parsed.get(item)):
        return

    bucket_sizes = metrics["BucketSizeBytes"]
    storage_infos = []
    for storage_type, value in bucket_sizes.items():
        storage_infos.append(f"{storage_type}: {render.bytes(value)}")
    sum_size = sum(bucket_sizes.values())
    yield check_levels(
        sum_size,
        "aws_bucket_size",
        params.get("bucket_size_levels", (None, None)),
        human_readable_func=render.bytes,
        infoname="Bucket size",
    )
    if storage_infos:
        yield 0, ", ".join(storage_infos)

    num_objects = sum(metrics["NumberOfObjects"].values())
    yield 0, "Number of objects: %s" % int(num_objects), [("aws_num_objects", num_objects)]

    location = metrics.get("LocationConstraint")
    if location:
        yield 0, "Location: %s" % location

    tag_infos = []
    for tag in metrics.get("Tagging", {}):
        tag_infos.append("{}: {}".format(tag["Key"], tag["Value"]))
    if tag_infos:
        yield 0, "[Tags] %s" % ", ".join(tag_infos)


def discover_aws_s3(p):
    return inventory_aws_generic(p, ["BucketSizeBytes", "NumberOfObjects"])


check_info["aws_s3"] = LegacyCheckDefinition(
    name="aws_s3",
    parse_function=parse_aws_s3,
    service_name="AWS/S3 Objects %s",
    discovery_function=discover_aws_s3,
    check_function=check_aws_s3_objects,
    check_ruleset_name="aws_s3_buckets_objects",
)

# .
#   .--summary-------------------------------------------------------------.
#   |                                                                      |
#   |           ___ _   _ _ __ ___  _ __ ___   __ _ _ __ _   _             |
#   |          / __| | | | '_ ` _ \| '_ ` _ \ / _` | '__| | | |            |
#   |          \__ \ |_| | | | | | | | | | | | (_| | |  | |_| |            |
#   |          |___/\__,_|_| |_| |_|_| |_| |_|\__,_|_|   \__, |            |
#   |                                                    |___/             |
#   '----------------------------------------------------------------------'


def discover_aws_s3_summary(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_aws_s3_summary(item, params, parsed):
    sum_size = 0
    largest_bucket = None
    largest_bucket_size = 0
    for bucket_name, bucket in parsed.items():
        bucket_size = sum(bucket["BucketSizeBytes"].values())
        sum_size += bucket_size
        if bucket_size >= largest_bucket_size:
            largest_bucket = bucket_name
            largest_bucket_size = bucket_size
    yield check_levels(
        sum_size,
        "aws_bucket_size",
        params.get("bucket_size_levels", (None, None)),
        human_readable_func=render.bytes,
        infoname="Total size",
    )

    if largest_bucket:
        yield (
            0,
            f"Largest bucket: {largest_bucket} ({render.bytes(largest_bucket_size)})",
            [("aws_largest_bucket_size", largest_bucket_size)],
        )


check_info["aws_s3.summary"] = LegacyCheckDefinition(
    name="aws_s3_summary",
    service_name="AWS/S3 Summary",
    sections=["aws_s3"],
    discovery_function=discover_aws_s3_summary,
    check_function=check_aws_s3_summary,
    check_ruleset_name="aws_s3_buckets",
)
