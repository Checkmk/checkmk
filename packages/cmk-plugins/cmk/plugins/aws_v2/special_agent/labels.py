#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The host labels of the piggyback hosts that stand for one AWS resource.

Every such host gets the same basic labels, so that users can find all AWS hosts of one
region or resource type. The runner adds the labels that every AWS host gets, such as
the account.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from cmk.plugins.lib.labels import ensure_valid_labels


@dataclass(frozen=True, kw_only=True)
class AwsResource:
    """The AWS resource that the host of a section result stands for.

    The name is the name of the resource in AWS, not the name of its host. It stays the
    same when the host naming changes. A CloudFront distribution has no name. The resource
    ID is the ID that AWS gives the resource. A resource without one, such as an S3
    bucket, has its name as ID, because AWS uses the name to identify it. So every
    resource host has this label, and users can filter on it without knowing the resource
    type. A global resource, such as a CloudFront distribution, has no region. The tags
    are the AWS tags of the resource that the rule imports, as process_tags_for_cmk_labels
    gives them.

    Of a resource that is gone from its summary since its metrics were cached, only the
    service is known. Every other resource has its ID.
    """

    service: str
    name: str | None = None
    resource_id: str | None = None
    region: str | None = None
    tags: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.resource_id is None and (
            self.name is not None or self.region is not None or self.tags
        ):
            raise ValueError(f"{self.service} resource {self.name!r} without a resource ID")

    def labels(self) -> Mapping[str, str]:
        """The labels of the host of the resource."""
        return {
            "cmk/aws/service": self.service,
            **({} if self.name is None else {"cmk/aws/name": self.name}),
            **({} if self.resource_id is None else {"cmk/aws/resource_id": self.resource_id}),
            **({} if self.region is None else {"cmk/aws/region": self.region}),
            **{
                f"cmk/aws/tag/{key}": value for key, value in ensure_valid_labels(self.tags).items()
            },
        }

    def metadata(self) -> Mapping[str, object]:
        """The inventory data of the host of the resource. The tags stay as AWS has them."""
        return {
            "entity": "resource",
            "service": self.service,
            **({} if self.name is None else {"name": self.name}),
            **({} if self.resource_id is None else {"resource_id": self.resource_id}),
            **({} if self.region is None else {"region": self.region}),
            "tags": dict(self.tags),
        }
