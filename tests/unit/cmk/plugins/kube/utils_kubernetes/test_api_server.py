#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disallow-untyped-defs
import json
import logging
from collections.abc import Mapping, Sequence
from unittest.mock import patch

import polyfactory.factories.pydantic_factory
import pytest
import requests

from cmk.plugins.kube import common, query
from cmk.plugins.kube.api_server import (
    _verify_version_support,
    CoreAPI,
    decompose_git_version,
    UnsupportedEndpointData,
    version_from_json,
)
from cmk.plugins.kube.schemata import api


class APISessionConfigFactory(polyfactory.factories.pydantic_factory.ModelFactory):
    __model__ = query.APISessionConfig


@pytest.fixture(name="core_api")
def _core_api() -> CoreAPI:
    config = APISessionConfigFactory.build(api_server_endpoint="http://api-unittest")
    client = query.make_api_client_requests(config, common.LOGGER)
    return CoreAPI(config, client)


CALL_API = "cmk.plugins.kube.api_server.send_request"
SUPPORTED_VERSION_STR = "Supported versions are v1.26, v1.27, v1.28, v1.29, v1.30, v1.31."


def test_raw_api_get_healthz_ok(core_api: CoreAPI) -> None:
    with patch(CALL_API) as mock_request:
        response = requests.Response()
        response.status_code = 200
        response._content = b"response-ok"
        mock_request.return_value = response
        result = core_api._get_healthz("/some_health_endpoint")
    assert result.status_code == 200
    assert result.response == "response-ok"


def test_raw_api_get_healthz_nok(core_api: CoreAPI) -> None:
    with patch(CALL_API) as mock_request:
        response = requests.Response()
        response.status_code = 500
        response._content = b"response-nok"
        mock_request.return_value = response
        result = core_api._get_healthz("/some_health_endpoint")

    assert result.status_code == 500
    assert result.response == "response-nok"


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
        api.KubernetesVersion(git_version=api.GitVersion("v1.22.2"), major=1, minor=22),
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
        api.KubernetesVersion(git_version=api.GitVersion("v1.24.0"), major=1, minor=24),
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
        api.KubernetesVersion(git_version=api.GitVersion("v1.16.0"), major=1, minor=16),
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
        api.KubernetesVersion(git_version=api.GitVersion("v1.21.9-eks-0d102a7"), major=1, minor=21),
        id="AWS cluster, eks flavor, supported version",
    ),
]


@pytest.mark.parametrize("version_json, _", version_json_pytest_params)
def test_version_endpoint(
    version_json: Mapping[str, str], _: api.KubernetesVersion, core_api: CoreAPI
) -> None:
    # arrange
    version_json_dump = json.dumps(version_json)
    response = requests.Response()
    response.status_code = 200
    response._content = version_json_dump.encode("utf-8")
    # act
    with patch(CALL_API) as mock_request:
        mock_request.return_value = response
        queried_version = core_api.query_raw_version()
    # assert
    assert queried_version == version_json_dump


def test_version_endpoint_no_json(core_api: CoreAPI) -> None:
    """

    Invalid endpoint, since returned data is not json. RawAPI will not
    identify this issue. Instead, the issue needs to be handled separately.
    """
    response = requests.Response()
    response.status_code = 200
    response._content = b"I'm not json"
    with patch(CALL_API) as mock_request:
        mock_request.return_value = response
        result = core_api.query_raw_version()
    assert result == "I'm not json"


def test_version_endpoint_invalid_json(core_api: CoreAPI) -> None:
    """

    Invalid endpoint, since gitVersion field is missing. RawAPI will not
    identify this issue. Instead, the issue needs to be handled separately.
    """

    # arrange
    response = requests.Response()
    response.status_code = 200
    response._content = b"{}"
    # act
    with patch(CALL_API) as mock_request:
        mock_request.return_value = response
        queried_version = core_api.query_raw_version()
    # assert
    assert queried_version == "{}"


@pytest.mark.parametrize("version_json, result", version_json_pytest_params)
def test_version_from_json(
    version_json: Mapping[str, str],
    result: api.UnknownKubernetesVersion | api.KubernetesVersion,
) -> None:
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
def test_version_from_json_invalid_json(data: str, message: str) -> None:
    with pytest.raises(UnsupportedEndpointData) as excinfo:
        version_from_json(data)
    assert str(excinfo.value) == message


formatter = logging.Formatter("%(levelname)s %(message)s")


@pytest.mark.parametrize(
    "git_version, result, logs",
    [
        (
            "",
            api.UnknownKubernetesVersion(git_version=api.GitVersion("")),
            [
                "ERROR Could not parse version string '', using regex from kubectl "
                "'\\s*v?([0-9]+(?:\\.[0-9]+)*).*'.",
            ],
        ),
        (
            "v1.21.0",
            api.KubernetesVersion(git_version=api.GitVersion("v1.21.0"), major=1, minor=21),
            [],
        ),
        (
            "v1.22.1",
            api.KubernetesVersion(git_version=api.GitVersion("v1.22.1"), major=1, minor=22),
            [],
        ),
        (
            "v1.23.2",
            api.KubernetesVersion(git_version=api.GitVersion("v1.23.2"), major=1, minor=23),
            [],
        ),
        (
            "1",
            api.UnknownKubernetesVersion(git_version=api.GitVersion("1")),
            [
                "ERROR Could not parse version string '1', version '1' has no minor.",
            ],
        ),
        (
            "0.1",
            api.KubernetesVersion(git_version=api.GitVersion("0.1"), major=0, minor=1),
            [],
        ),
        (
            "1.01",
            api.UnknownKubernetesVersion(git_version=api.GitVersion("1.01")),
            [
                "ERROR Could not parse version string '1.01', a version component is "
                "zero-prefixed.",
            ],
        ),
    ],
)
def test_decompose_git_version(
    git_version: api.GitVersion,
    result: api.KubernetesVersion | api.UnknownKubernetesVersion,
    logs: Sequence[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARN):
        assert result == decompose_git_version(git_version)
    assert [formatter.format(record) for record in caplog.records] == logs


@pytest.mark.parametrize(
    "kubernetes_version, logs",
    [
        (
            api.UnknownKubernetesVersion(git_version=api.GitVersion("")),
            [
                "WARNING Unsupported Kubernetes version ''. " + SUPPORTED_VERSION_STR,
                "WARNING Processing data is done on a best effort basis.",
            ],
        ),
        (
            api.KubernetesVersion(git_version=api.GitVersion("v1.26.2"), major=1, minor=26),
            [],
        ),
        (
            api.KubernetesVersion(git_version=api.GitVersion("v1.27.0"), major=1, minor=27),
            [],
        ),
        (
            api.KubernetesVersion(git_version=api.GitVersion("v1.32.0"), major=1, minor=32),
            [
                "WARNING Unsupported Kubernetes version 'v1.32.0'. " + SUPPORTED_VERSION_STR,
                "WARNING Processing data is done on a best effort basis.",
            ],
        ),
    ],
)
def test__verify_version_support_continue_processing(
    kubernetes_version: api.KubernetesVersion | api.UnknownKubernetesVersion,
    logs: Sequence[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARN):
        _verify_version_support(kubernetes_version)
    assert [formatter.format(record) for record in caplog.records] == logs


@pytest.mark.parametrize(
    "kubernetes_version, message",
    [
        (
            api.KubernetesVersion(git_version=api.GitVersion("v1.16.0"), major=1, minor=16),
            "Unsupported Kubernetes version 'v1.16.0'. Aborting processing API data. "
            + SUPPORTED_VERSION_STR,
        ),
        (
            api.KubernetesVersion(git_version=api.GitVersion("1.14.0"), major=1, minor=14),
            "Unsupported Kubernetes version '1.14.0'. Aborting processing API data. "
            + SUPPORTED_VERSION_STR,
        ),
    ],
)
def test__verify_version_support_abort_processing(
    kubernetes_version: api.KubernetesVersion | api.UnknownKubernetesVersion,
    message: str,
) -> None:
    with pytest.raises(UnsupportedEndpointData) as excinfo:
        _verify_version_support(kubernetes_version)
    assert str(excinfo.value) == message
