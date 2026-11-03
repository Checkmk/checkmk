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
