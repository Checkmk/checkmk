#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from kubernetes import client  # type: ignore[import-untyped]
from kubernetes.client import ApiClient  # type: ignore[import-untyped]


def kubernetes_api_client():
    config = client.Configuration()
    config.host = "http://dummy"
    config.api_key_prefix["authorization"] = "Bearer"
    config.api_key["authorization"] = "dummy"
    config.verify_ssl = False
    return ApiClient(config)


@pytest.fixture
def core_client():
    return client.CoreV1Api(kubernetes_api_client())


@pytest.fixture
def batch_client():
    return client.BatchV1Api(kubernetes_api_client())


@pytest.fixture
def apps_client():
    return client.AppsV1Api(kubernetes_api_client())


@pytest.fixture
def dummy_host():
    return kubernetes_api_client().configuration.host
