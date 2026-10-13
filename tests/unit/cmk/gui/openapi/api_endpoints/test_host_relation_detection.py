#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from http import HTTPStatus

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry, HostRelationDetectionClient, Response


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda client: client.suggest(expect_ok=False), id="suggest"),
        pytest.param(lambda client: client.scan(expect_ok=False), id="scan"),
        pytest.param(
            lambda client: client.accept(
                scan_id="relation_scan-any", findings=["word:ilo"], expect_ok=False
            ),
            id="accept",
        ),
        pytest.param(lambda client: client.show("relation_scan-any", expect_ok=False), id="show"),
        pytest.param(lambda client: client.rows("relation_scan-any", expect_ok=False), id="rows"),
    ],
)
def test_the_relation_detection_needs_the_permission_to_change_setup(
    clients: ClientRegistry, call: Callable[[HostRelationDetectionClient], Response]
) -> None:
    clients.UserRole.clone(body={"role_id": "admin", "new_role_id": "no_setup_changes"})
    clients.UserRole.edit(role_id="no_setup_changes", body={"new_permissions": {"wato.edit": "no"}})
    clients.User.create(
        username="reader",
        fullname="Reader",
        auth_option={"auth_type": "password", "password": "reader-password"},
        roles=["no_setup_changes"],
    )
    clients.HostRelationDetection.set_credentials("reader", "reader-password")

    call(clients.HostRelationDetection).assert_status_code(HTTPStatus.FORBIDDEN)


def test_a_scan_pairs_by_custom_host_attributes_only(clients: ClientRegistry) -> None:
    clients.HostRelationDetection.scan(
        findings=[
            {
                "id": "attribute:ipaddress",
                "kind": "management",
                "paired_by": {"source": "attribute", "name": "ipaddress"},
            }
        ],
        expect_ok=False,
    ).assert_status_code(HTTPStatus.BAD_REQUEST)


def test_suggestions_are_asked_for_custom_host_attributes_only(clients: ClientRegistry) -> None:
    clients.HostRelationDetection.suggest(
        values=[{"source": "attribute", "name": "alias"}], expect_ok=False
    ).assert_status_code(HTTPStatus.BAD_REQUEST)
