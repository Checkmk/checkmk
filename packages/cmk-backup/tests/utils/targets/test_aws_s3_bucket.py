#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator
from pathlib import Path

import pytest
from botocore.stub import Stubber

from cmk.backup.utils.targets.aws_s3_bucket import _client_args, S3Bucket, S3Params


class TestS3BucketEndpointUrl:
    def test_s3_bucket_without_endpoint_url_defaults_to_s3(self) -> None:
        params: S3Params = {
            "access_key": "test-access-key",
            "secret": "test-password-id",
            "bucket": "test-bucket",
        }
        assert _client_args(params, "test-secret-key") == {
            "aws_access_key_id": "test-access-key",
            "aws_secret_access_key": "test-secret-key",
        }

    def test_s3_bucket_with_empty_endpoint_url_defaults_to_s3(self) -> None:
        params: S3Params = {
            "access_key": "test-access-key",
            "secret": "test-password-id",
            "bucket": "test-bucket",
            "endpoint_url": "",
        }
        assert _client_args(params, "test-secret-key") == {
            "aws_access_key_id": "test-access-key",
            "aws_secret_access_key": "test-secret-key",
        }

    @pytest.mark.parametrize(
        "endpoint_url",
        [
            "https://s3.us-west-000.backblazeb2.com",
            "https://minio.example.com:9000",
            "https://s3.eu-central-1.wasabisys.com",
            "http://localhost:9000",
        ],
    )
    def test_s3_bucket_with_various_endpoints(self, endpoint_url: str) -> None:
        params: S3Params = {
            "access_key": "test-access-key",
            "secret": "test-password-id",
            "bucket": "test-bucket",
            "endpoint_url": endpoint_url,
        }
        assert _client_args(params, "test-secret-key") == {
            "aws_access_key_id": "test-access-key",
            "aws_secret_access_key": "test-secret-key",
            "endpoint_url": endpoint_url,
        }


@pytest.fixture(name="bucket")
def fixture_bucket() -> S3Bucket:
    return S3Bucket({"access_key": "key", "secret": ("password", "secret"), "bucket": "backups"})


@pytest.fixture(name="stubber")
def fixture_stubber(bucket: S3Bucket) -> Iterator[Stubber]:
    with Stubber(bucket.client) as stubber:
        yield stubber
    stubber.assert_no_pending_responses()


def test_empty_bucket_has_no_objects(bucket: S3Bucket, stubber: Stubber) -> None:
    stubber.add_response(
        "list_objects_v2",
        {"Name": "backups", "KeyCount": 0, "IsTruncated": False},
        {"Bucket": "backups"},
    )

    assert not list(bucket.objects())


def test_objects_of_all_pages(bucket: S3Bucket, stubber: Stubber) -> None:
    stubber.add_response(
        "list_objects_v2",
        {
            "Name": "backups",
            "KeyCount": 1,
            "IsTruncated": True,
            "NextContinuationToken": "page-2",
            "Contents": [{"Key": "backup-1"}],
        },
        {"Bucket": "backups"},
    )
    stubber.add_response(
        "list_objects_v2",
        {"Name": "backups", "KeyCount": 1, "IsTruncated": False, "Contents": [{"Key": "backup-2"}]},
        {"Bucket": "backups", "ContinuationToken": "page-2"},
    )

    assert list(bucket.objects()) == [Path("backup-1"), Path("backup-2")]
