#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import gzip
import uuid
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import (
    RelayConfigTask,
    TaskListResponse,
    TaskResponse,
)
from cmk.testlib.agent_receiver.clients import RelayClient, SiteClient
from cmk.testlib.agent_receiver.relay_config_generator import assert_config_tar
from cmk.testlib.agent_receiver.site_mock import SiteMock

_GZIP_MAGIC = b"\x1f\x8b"


@pytest.mark.parametrize(
    "config_encoding",
    [
        pytest.param("gzip", id="only gzip"),
        pytest.param("zstd, gzip", id="gzip among unknown encodings"),
    ],
)
def test_relay_accepting_gzip_gets_compressed_config(
    test_client: TestClient,
    site: SiteMock,
    config_encoding: str,
) -> None:
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])
    config = site.push_config([relay_id])
    SiteClient(test_client, site.site_name).activate_config()
    relay = RelayClient(test_client, site.site_name, relay_id)

    response = relay.get_tasks(status="PENDING", config_encoding=config_encoding)

    assert response.status_code == HTTPStatus.OK, response.text
    spec = _config_task_spec(response.json())
    assert spec.tar_data.startswith(_GZIP_MAGIC)
    assert_config_tar(config, relay_id, gzip.decompress(spec.tar_data))


def test_relay_predating_the_header_gets_uncompressed_config(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])
    config = site.push_config([relay_id])
    SiteClient(test_client, site.site_name).activate_config()
    relay = RelayClient(test_client, site.site_name, relay_id)

    response = relay.get_tasks(status="PENDING", config_encoding=None)

    assert response.status_code == HTTPStatus.OK, response.text
    spec = _config_task_spec(response.json())
    assert not spec.tar_data.startswith(_GZIP_MAGIC)
    assert_config_tar(config, relay_id, spec.tar_data)


def test_relay_announcing_only_unsupported_encodings_gets_uncompressed_config(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])
    config = site.push_config([relay_id])
    SiteClient(test_client, site.site_name).activate_config()
    relay = RelayClient(test_client, site.site_name, relay_id)

    response = relay.get_tasks(status="PENDING", config_encoding="zstd")

    assert response.status_code == HTTPStatus.OK, response.text
    spec = _config_task_spec(response.json())
    assert not spec.tar_data.startswith(_GZIP_MAGIC)
    assert_config_tar(config, relay_id, spec.tar_data)


@pytest.mark.parametrize(
    "config_encoding",
    [
        pytest.param("", id="empty"),
        pytest.param(" , ", id="only separators"),
        pytest.param("gzip;q=0", id="gzip with parameter"),
    ],
)
def test_relay_sending_malformed_header_gets_uncompressed_config(
    test_client: TestClient,
    site: SiteMock,
    config_encoding: str,
) -> None:
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])
    config = site.push_config([relay_id])
    SiteClient(test_client, site.site_name).activate_config()
    relay = RelayClient(test_client, site.site_name, relay_id)

    response = relay.get_tasks(status="PENDING", config_encoding=config_encoding)

    assert response.status_code == HTTPStatus.OK, response.text
    spec = _config_task_spec(response.json())
    assert not spec.tar_data.startswith(_GZIP_MAGIC)
    assert_config_tar(config, relay_id, spec.tar_data)


def test_etag_of_gzip_config_does_not_match_uncompressed_config(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])
    site.push_config([relay_id])
    SiteClient(test_client, site.site_name).activate_config()
    relay = RelayClient(test_client, site.site_name, relay_id)
    gzip_etag = relay.get_tasks(status="PENDING", config_encoding="gzip").headers["ETag"]

    # Act as a relay predating the header.
    response = relay.get_tasks(status="PENDING", if_none_match=gzip_etag, config_encoding=None)

    assert response.status_code == HTTPStatus.OK, response.text
    assert not _config_task_spec(response.json()).tar_data.startswith(_GZIP_MAGIC)


def test_relay_accepting_gzip_gets_compressed_config_when_reporting_result(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    relay_id = str(uuid.uuid4())
    site.set_scenario([relay_id])
    config = site.push_config([relay_id])
    SiteClient(test_client, site.site_name).activate_config()
    relay = RelayClient(test_client, site.site_name, relay_id)
    (task,) = relay.get_task_list(status="PENDING").tasks

    response = relay.update_task(task.id, "OK", "", config_encoding="gzip")

    assert response.status_code == HTTPStatus.ACCEPTED, response.text
    spec = TaskResponse.model_validate(response.json()).spec
    assert isinstance(spec, RelayConfigTask)
    assert spec.tar_data.startswith(_GZIP_MAGIC)
    assert_config_tar(config, relay_id, gzip.decompress(spec.tar_data))


def _config_task_spec(body: object) -> RelayConfigTask:
    (spec,) = [
        task.spec
        for task in TaskListResponse.model_validate(body).tasks
        if isinstance(task.spec, RelayConfigTask)
    ]
    return spec
