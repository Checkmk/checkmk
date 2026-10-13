#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest
from kubernetes import client
from kubernetes.client import (  # type: ignore[attr-defined]
    ApiClient,
    AppsV1Api,
    BatchV1Api,
    CoreV1Api,
)


def kubernetes_api_client() -> ApiClient:
    config = client.Configuration()  # type: ignore[attr-defined]
    config.host = "http://dummy"
    config.api_key_prefix["authorization"] = "Bearer"
    config.api_key["authorization"] = "dummy"
    config.verify_ssl = False
    return ApiClient(config)


@pytest.fixture
def core_client() -> CoreV1Api:
    return CoreV1Api(kubernetes_api_client())


@pytest.fixture
def batch_client() -> BatchV1Api:
    return BatchV1Api(kubernetes_api_client())


@pytest.fixture
def apps_client() -> AppsV1Api:
    return AppsV1Api(kubernetes_api_client())


@pytest.fixture
def dummy_host() -> str:
    return str(kubernetes_api_client().configuration.host)
