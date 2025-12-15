#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import Request
from cmk.gui.pages import PageContext, PageRegistry
from cmk.gui.product_telemetry import download
from cmk.gui.product_telemetry.download import PageDownloadProductTelemetry
from cmk.product_telemetry.schema import ProductTelemetryPayload


@pytest.fixture(name="page_context")
def fixture_page_context(request_context: Request) -> PageContext:
    return PageContext(
        config=Config(),
        request=request_context,
    )


@pytest.fixture(name="mock_telemetry_data")
def fixture_mock_telemetry_data() -> ProductTelemetryPayload:
    return ProductTelemetryPayload(
        timestamp=1234567890,
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        count_hosts=10,
        count_services=50,
        count_folders=5,
        edition="pro",
        cmk_version="2.5.0",
        checks={},
        grafana=None,
    )


def test_page_download_telemetry_register() -> None:
    page_registry = PageRegistry()
    download.register(page_registry)

    assert "download_telemetry" in page_registry

    endpoint = page_registry.get("download_telemetry")
    assert endpoint is not None
    assert isinstance(endpoint.handler, PageDownloadProductTelemetry)


def test_page_download_telemetry_success(
    page_context: PageContext,
    mocker: MockerFixture,
    mock_telemetry_data: ProductTelemetryPayload,
) -> None:
    mock_user = mocker.patch("cmk.gui.product_telemetry.download.user")
    mock_user.need_permission = mocker.Mock()

    mock_collect = mocker.patch(
        "cmk.gui.product_telemetry.download.collect_telemetry_data",
        return_value=mock_telemetry_data,
    )

    mock_response = mocker.patch("cmk.gui.product_telemetry.download.response")
    mock_response.set_content_type = mocker.Mock()
    mock_response.set_content_disposition = mocker.Mock()
    mock_response.set_data = mocker.Mock()

    page = PageDownloadProductTelemetry()
    page.page(page_context)

    mock_user.need_permission.assert_called_once_with("general.download_product_telemetry")

    mock_collect.assert_called_once()

    mock_response.set_content_type.assert_called_once_with("application/json")
    mock_response.set_content_disposition.assert_called_once_with(
        "attachment", "checkmk_telemetry.json"
    )

    assert mock_response.set_data.call_count == 1
    call_args = mock_response.set_data.call_args[0][0]

    json_data = json.loads(call_args.decode("utf-8"))
    assert json_data["timestamp"] == 1234567890
    assert json_data["id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert json_data["count_hosts"] == 10
    assert json_data["count_services"] == 50
    assert json_data["count_folders"] == 5
    assert json_data["edition"] == "pro"
    assert json_data["cmk_version"] == "2.5.0"


def test_page_download_telemetry_permission_denied(
    page_context: PageContext,
    mocker: MockerFixture,
) -> None:
    mock_user = mocker.patch("cmk.gui.product_telemetry.download.user")
    mock_user.need_permission = mocker.Mock(side_effect=MKAuthException("Permission denied"))

    page = PageDownloadProductTelemetry()

    with pytest.raises(MKAuthException, match="Permission denied"):
        page.page(page_context)

    mock_user.need_permission.assert_called_once_with("general.download_product_telemetry")
