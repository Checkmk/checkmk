#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.ldap_integration._diagnostics import diagnostic_tests
from cmk.gui.ldap_integration.ldap_connector import LDAPUserConnector
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.shared_endpoint_families.ldap_connection import LDAP_CONNECTION_FAMILY
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.userdb import get_connection
from cmk.gui.utils import permission_verification as permissions


@api_model
class LDAPConnectionTestResult:
    title: str = api_field(
        description="The name of the diagnostic test.",
        example="Connection",
    )
    success: bool = api_field(
        description="Whether the test was successful.",
        example=True,
    )
    details: str = api_field(
        description="Details about the test result.",
        example="Connection established. The connection settings seem to be OK.",
    )


@api_model
class LDAPServerTestResults:
    server: str = api_field(
        description="The address of the LDAP server the tests were run against.",
        example="10.200.3.32",
    )
    results: list[LDAPConnectionTestResult] = api_field(
        description="The results of the individual diagnostic tests.",
    )


@api_model
class LDAPConnectionTestResponse:
    connection_id: str = api_field(
        description="The ID of the tested LDAP connection.",
        example="LDAP_1",
    )
    success: bool = api_field(
        description="Whether all diagnostic tests on all servers were successful.",
        example=True,
    )
    servers: list[LDAPServerTestResults] = api_field(
        description="The test results, grouped by LDAP server address.",
    )


def test_ldap_connection_v1(
    ldap_connection_id: Annotated[
        str,
        PathParam(description="The LDAP connection ID.", example="LDAP_1"),
    ],
) -> LDAPConnectionTestResponse:
    """Test an LDAP connection

    Runs the same diagnostic tests as the "Save & test" feature of the LDAP connection
    configuration page against the saved connection: connecting to each configured server,
    looking up the user and group base DNs, counting users and groups and checking the
    groups-to-roles sync plug-in. The configuration is not modified.
    """
    user.need_permission("wato.seeall")
    user.need_permission("wato.users")

    connection = get_connection(ldap_connection_id)
    if not isinstance(connection, LDAPUserConnector):
        raise ProblemException(404, f"The LDAP connection '{ldap_connection_id}' does not exist.")

    servers = []
    try:
        for address in connection.servers():
            results = []
            for title, test_func in diagnostic_tests():
                try:
                    state, msg = test_func(connection, address)
                except Exception as e:
                    state = False
                    msg = f"Exception: {e}"
                    logger.exception("error testing LDAP %s for %s", title, address)
                results.append(
                    LDAPConnectionTestResult(title=title, success=state, details=msg or "")
                )
            servers.append(LDAPServerTestResults(server=address, results=results))
    finally:
        connection.disconnect()

    return LDAPConnectionTestResponse(
        connection_id=ldap_connection_id,
        success=all(result.success for server in servers for result in server.results),
        servers=servers,
    )


ENDPOINT_TEST_LDAP_CONNECTION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("ldap_connection", "{ldap_connection_id}", "test"),
        link_relation="cmk/verify",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                permissions.Perm("wato.seeall"),
                permissions.Perm("wato.users"),
            ]
        )
    ),
    doc=EndpointDoc(family=LDAP_CONNECTION_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=test_ldap_connection_v1)},
)
