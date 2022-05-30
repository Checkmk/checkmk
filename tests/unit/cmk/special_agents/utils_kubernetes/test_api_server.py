#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from typing import Mapping, Sequence, Union

import pytest
from kubernetes import client  # type: ignore[import]
from kubernetes.client import ApiClient  # type: ignore[import]
from mocket import Mocketizer  # type: ignore[import]
from mocket.mockhttp import Entry  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.api_server import (
    _verify_version_support,
    decompose_git_version,
    RawAPI,
    UnsupportedEndpointData,
    version_from_json,
)
from cmk.special_agents.utils_kubernetes.schemata import api


def kubernetes_api_client():
    config = client.Configuration()
    config.host = "http://api-unittest"
    return ApiClient(config)


@pytest.fixture(name="raw_api")
def _raw_api():
    return RawAPI(kubernetes_api_client(), timeout=(10, 10))


def test_raw_api_get_healthz_ok(raw_api):
    Entry.single_register(Entry.GET, "http://api-unittest/some_health_endpoint", body="response-ok")
    with Mocketizer():
        result = raw_api._get_healthz("/some_health_endpoint")

    assert result.status_code == 200
    assert result.response == "response-ok"
    assert result.verbose_response is None


def test_raw_api_get_healthz_nok(raw_api):
    Entry.single_register(
        Entry.GET, "http://api-unittest/some_health_endpoint", body="response-nok", status=500
    )
    Entry.single_register(
        Entry.GET,
        "http://api-unittest/some_health_endpoint?verbose=1",
        body="verbose\nresponse\nnok",
        status=500,
    )
    with Mocketizer():
        result = raw_api._get_healthz("/some_health_endpoint")

    assert result.status_code == 500
    assert result.response == "response-nok"
    assert result.verbose_response == "verbose\nresponse\nnok"


version_json_pytest_params = [
    pytest.param(
        {
            "major": "1",
            "minor": "22",
            "gitVersion": "v1.22.2",
            "gitCommit": "8b5a19147530eaac9476b0ab82980b4088bbc1b2",
            "gitTreeState": "clean",
            "buildDate": "2021-09-15T21:32:41Z",
            "goVersion": "go1.16.8",
            "compiler": "gc",
            "platform": "linux/amd64",
        },
        api.KubernetesVersion(git_version="v1.22.2", major=1, minor=22),
        id="Vanilla Kubernetes cluster, supported version",
    ),
    pytest.param(
        {
            "major": "1",
            "minor": "24",
            "gitVersion": "v1.24.0",
            "gitCommit": "4ce5a8954017644c5420bae81d72b09b735c21f0",
            "gitTreeState": "clean",
            "buildDate": "2022-05-03T13:38:19Z",
            "goVersion": "go1.18.1",
            "compiler": "gc",
            "platform": "linux/amd64",
        },
        api.KubernetesVersion(git_version="v1.24.0", major=1, minor=24),
        id="Minikube, untested version",
    ),
    pytest.param(
        {
            "major": "1",
            "minor": "16",
            "gitVersion": "v1.16.0",
            "gitCommit": "2bd9643cee5b3b3a5ecbd3af49d09018f0773c77",
            "gitTreeState": "clean",
            "buildDate": "2019-09-18T14:27:17Z",
            "goVersion": "go1.12.9",
            "compiler": "gc",
            "platform": "linux/amd64",
        },
        api.KubernetesVersion(git_version="v1.16.0", major=1, minor=16),
        id="Minikube, outdated version",
    ),
    pytest.param(
        {
            "major": "1",
            "minor": "21+",
            "gitVersion": "v1.21.9-eks-0d102a7",
            "gitCommit": "eb09fc479c1b2bfcc35c47416efb36f1b9052d58",
            "gitTreeState": "clean",
            "buildDate": "2022-02-17T16:36:28Z",
            "goVersion": "go1.16.12",
            "compiler": "gc",
            "platform": "linux/amd64",
        },
        api.KubernetesVersion(git_version="v1.21.9-eks-0d102a7", major=1, minor=21),
        id="AWS cluster, eks flavor, supported version",
    ),
]


@pytest.mark.parametrize("version_json, _", version_json_pytest_params)
def test_version_endpoint(version_json: Mapping[str, str], _, raw_api):
    # arrange
    version_json_dump = json.dumps(version_json)
    Entry.single_register(
        Entry.GET,
        "http://api-unittest/version",
        body=version_json_dump,
        headers={"content-type": "application/json"},
    )
    # act
    with Mocketizer():
        queried_version = raw_api.query_raw_version()
    # assert
    assert queried_version == version_json_dump


def test_version_endpoint_no_json(raw_api):
    """

    Invalid endpoint, since returned data is not json. RawAPI will not
    identify this issue. Instead, the issue needs to be handled seperately.
    """
    Entry.single_register(Entry.GET, "http://api-unittest/version", body="I'm not json")
    with Mocketizer():
        result = raw_api.query_raw_version()
    assert result == "I'm not json"


def test_version_endpoint_invalid_json(raw_api):
    """

    Invalid endpoint, since gitVersion field is missing. RawAPI will not
    identify this issue. Instead, the issue needs to be handled seperately.
    """

    # arrange
    Entry.single_register(
        Entry.GET,
        "http://api-unittest/version",
        body=json.dumps({}),
        headers={"content-type": "application/json"},
    )
    # act
    with Mocketizer():
        queried_version = raw_api.query_raw_version()
    # assert
    assert queried_version == "{}"


@pytest.mark.parametrize("version_json, result", version_json_pytest_params)
def test_version_from_json(version_json: Mapping[str, str], result):
    assert result == version_from_json(json.dumps(version_json))


@pytest.mark.parametrize(
    "data, message",
    [
        (
            "I'm no json",
            "Unknown endpoint information at endpoint /version, HTTP(S) response was "
            "'I'm no json'.",
        ),
        (
            json.dumps({}),
            "Data from endpoint /version did not have mandatory field 'gitVersion', HTTP(S) "
            "response was '{}'.",
        ),
    ],
)
def test_version_from_json_invalid_json(data: str, message: str):
    with pytest.raises(UnsupportedEndpointData) as excinfo:
        version_from_json(data)
    assert str(excinfo.value) == message


formatter = logging.Formatter("%(levelname)s %(message)s")


@pytest.mark.parametrize(
    "git_version, result, logs",
    [
        (
            "",
            api.UnknownKubernetesVersion(git_version=""),
            [
                "ERROR Could not parse version string '', using regex from kubectl "
                "'\\s*v?([0-9]+(?:\\.[0-9]+)*).*'.",
            ],
        ),
        (
            "v1.21.0",
            api.KubernetesVersion(git_version="v1.21.0", major=1, minor=21),
            [],
        ),
        (
            "v1.22.1",
            api.KubernetesVersion(git_version="v1.22.1", major=1, minor=22),
            [],
        ),
        (
            "v1.23.2",
            api.KubernetesVersion(git_version="v1.23.2", major=1, minor=23),
            [],
        ),
        (
            "1",
            api.UnknownKubernetesVersion(git_version="1"),
            [
                "ERROR Could not parse version string '1', version '1' has no minor.",
            ],
        ),
        (
            "0.1",
            api.KubernetesVersion(git_version="0.1", major=0, minor=1),
            [],
        ),
        (
            "1.01",
            api.UnknownKubernetesVersion(git_version="1.01"),
            [
                "ERROR Could not parse version string '1.01', a version component is "
                "zero-prefixed.",
            ],
        ),
    ],
)
def test_decompose_git_version(
    git_version: str,
    result: Union[api.KubernetesVersion, api.UnknownKubernetesVersion],
    logs: Sequence[str],
    caplog,
):

    assert result == decompose_git_version(git_version)
    assert [formatter.format(record) for record in caplog.records] == logs


@pytest.mark.skip(
    reason="This test is causes the resilience tests to fail for unknown reasons. "
    "Further investigation required."
)
@pytest.mark.parametrize(
    "kubernetes_version, logs",
    [
        (
            api.UnknownKubernetesVersion(git_version=""),
            [
                "WARNING Unsupported Kubernetes version ''. "
                "Supported versions are v1.21, v1.22, v1.23.",
                "WARNING Processing data is done on a best effort basis.",
            ],
        ),
        (
            api.KubernetesVersion(git_version="v1.21.0", major=1, minor=21),
            [],
        ),
        (
            api.KubernetesVersion(git_version="v1.22.1", major=1, minor=22),
            [],
        ),
        (
            api.KubernetesVersion(git_version="v1.23.2", major=1, minor=23),
            [],
        ),
        (
            api.KubernetesVersion(git_version="v1.24.0", major=1, minor=24),
            [
                "WARNING Unsupported Kubernetes version 'v1.24.0'. "
                "Supported versions are v1.21, v1.22, v1.23.",
                "WARNING Processing data is done on a best effort basis.",
            ],
        ),
    ],
)
def test__verify_version_support_continue_processing(
    kubernetes_version: Union[api.KubernetesVersion, api.UnknownKubernetesVersion],
    logs: Sequence[str],
    caplog,
):

    _verify_version_support(kubernetes_version)
    assert [formatter.format(record) for record in caplog.records] == logs


@pytest.mark.parametrize(
    "kubernetes_version, message",
    [
        (
            api.KubernetesVersion(git_version="v1.16.0", major=1, minor=16),
            "Unsupported Kubernetes version 'v1.16.0'. API Servers with version < v1.21 are "
            "known to return incompatible data. Aborting processing API data. "
            "Supported versions are v1.21, v1.22, v1.23.",
        ),
        (
            api.KubernetesVersion(git_version="1.14.0", major=1, minor=14),
            "Unsupported Kubernetes version '1.14.0'. API Servers with version < v1.21 are "
            "known to return incompatible data. Aborting processing API data. "
            "Supported versions are v1.21, v1.22, v1.23.",
        ),
    ],
)
def test__verify_version_support_abort_processing(
    kubernetes_version: Union[api.KubernetesVersion, api.UnknownKubernetesVersion],
    message: str,
):

    with pytest.raises(UnsupportedEndpointData) as excinfo:
        _verify_version_support(kubernetes_version)
    assert str(excinfo.value) == message
