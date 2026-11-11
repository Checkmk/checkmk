#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.aws_v2.special_agent.labels import AwsResource


def test_resource_labels_make_the_tags_valid_labels() -> None:
    labels = AwsResource(
        service="s3",
        name="bucket",
        resource_id="bucket",
        region="eu-central-1",
        tags={"a:b": "", "c": "d:e"},
    ).labels()

    assert labels == {
        "cmk/aws/service": "s3",
        "cmk/aws/name": "bucket",
        "cmk/aws/resource_id": "bucket",
        "cmk/aws/region": "eu-central-1",
        "cmk/aws/tag/a_b": "true",
        "cmk/aws/tag/c": "d_e",
    }


def test_resource_of_only_a_service_labels_only_the_service() -> None:
    assert AwsResource(service="sns").labels() == {"cmk/aws/service": "sns"}


@pytest.mark.parametrize(
    "name, region, tags",
    [
        pytest.param("bucket", None, {}, id="name without ID -> error"),
        pytest.param(None, "eu-central-1", {}, id="region without ID -> error"),
        pytest.param(None, None, {"team": "a"}, id="tags without ID -> error"),
    ],
)
def test_resource_with_data_needs_its_id(
    name: str | None, region: str | None, tags: Mapping[str, str]
) -> None:
    with pytest.raises(ValueError):
        AwsResource(service="s3", name=name, region=region, tags=tags)


def test_resource_metadata_keeps_the_tags_as_aws_has_them() -> None:
    metadata = AwsResource(
        service="s3",
        name="bucket",
        resource_id="bucket",
        region="eu-central-1",
        tags={"a:b": "", "c": "d:e"},
    ).metadata()

    assert metadata == {
        "entity": "resource",
        "service": "s3",
        "name": "bucket",
        "resource_id": "bucket",
        "region": "eu-central-1",
        "tags": {"a:b": "", "c": "d:e"},
    }


def test_resource_metadata_has_the_arn_unchanged() -> None:
    metadata = AwsResource(
        service="lambda",
        arn="arn:aws:lambda:eu-central-1:123456789012:function:my-function",
    ).metadata()

    assert metadata == {
        "entity": "resource",
        "service": "lambda",
        "arn": "arn:aws:lambda:eu-central-1:123456789012:function:my-function",
        "tags": {},
    }


@pytest.mark.parametrize(
    "resource, expected_labels",
    [
        pytest.param(
            AwsResource(
                service="rds",
                name="my-db",
                resource_id="db-ABC",
                region="eu-central-1",
                arn="arn:aws:rds:eu-central-1:123456789012:db:my-db",
            ),
            {
                "cmk/aws/service": "rds",
                "cmk/aws/name": "my-db",
                "cmk/aws/resource_id": "db-ABC",
                "cmk/aws/region": "eu-central-1",
                "cmk/aws/arn": "arn:aws:rds:eu-central-1:123456789012:db:my-db",
            },
            id="ARN with colons -> label is the exact ARN",
        ),
        pytest.param(
            AwsResource(
                service="ecs",
                name="cluster",
                resource_id="cluster",
                region="us-east-1",
                arn="arn:aws:ecs:us-east-1:123456789012:cluster/cluster",
            ),
            {
                "cmk/aws/service": "ecs",
                "cmk/aws/name": "cluster",
                "cmk/aws/resource_id": "cluster",
                "cmk/aws/region": "us-east-1",
                "cmk/aws/arn": "arn:aws:ecs:us-east-1:123456789012:cluster/cluster",
            },
            id="ARN with slash -> label is the exact ARN",
        ),
        pytest.param(
            AwsResource(service="ec2", name="vm", resource_id="i-0", region="eu-central-1"),
            {
                "cmk/aws/service": "ec2",
                "cmk/aws/name": "vm",
                "cmk/aws/resource_id": "i-0",
                "cmk/aws/region": "eu-central-1",
            },
            id="no ARN -> no ARN label",
        ),
        pytest.param(
            AwsResource(
                service="lambda",
                arn="arn:aws:lambda:eu-central-1:123456789012:function:my-function",
            ),
            {
                "cmk/aws/service": "lambda",
                "cmk/aws/arn": "arn:aws:lambda:eu-central-1:123456789012:function:my-function",
            },
            id="ARN without resource ID -> service and ARN labels",
        ),
    ],
)
def test_resource_labels_have_the_arn_unchanged(
    resource: AwsResource, expected_labels: Mapping[str, str]
) -> None:
    assert resource.labels() == expected_labels
