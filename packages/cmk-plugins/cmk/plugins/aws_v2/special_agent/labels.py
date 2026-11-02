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

from cmk.plugins.lib.labels import ensure_valid_labels


def resource_labels(
    service: str,
    name: str | None,
    resource_id: str,
    region: str | None,
    tags: Mapping[str, str],
) -> Mapping[str, str]:
    """The labels of the host of one AWS resource.

    The name is the name of the resource in AWS, not the name of its host. It stays the
    same when the host naming changes. A CloudFront distribution has no name. The resource
    ID is the ID that AWS gives the resource. A resource without one, such as an S3
    bucket, has its name as ID, because AWS uses the name to identify it. So every
    resource host has this label, and users can filter on it without knowing the resource
    type. A global resource, such as a CloudFront distribution, has no region. The tags
    are the AWS tags of the resource that the rule imports, as process_tags_for_cmk_labels
    gives them.
    """
    return {
        "cmk/aws/service": service,
        **({} if name is None else {"cmk/aws/name": name}),
        "cmk/aws/resource_id": resource_id,
        **({} if region is None else {"cmk/aws/region": region}),
        **{f"cmk/aws/tag/{key}": value for key, value in ensure_valid_labels(tags).items()},
    }
