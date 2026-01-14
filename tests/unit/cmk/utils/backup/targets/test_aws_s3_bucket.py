#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.utils.backup.targets.aws_s3_bucket import _client_args, S3Params


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
