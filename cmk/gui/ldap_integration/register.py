#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.ldap_integration._openapi import register as openapi_register
from cmk.gui.ldap_integration.api import register as api_register
from cmk.gui.ldap_integration.ldap import register as ldap_register
from cmk.gui.openapi.framework.registry import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.userdb._connector import UserConnectorRegistry
from cmk.gui.watolib.analyze_configuration import ACTestRegistry
from cmk.gui.watolib.mode._registry import ModeRegistry

from . import ldap_connector
from ._ac_tests import ACTestLDAPSecured


def register(
    mode_registry: ModeRegistry,
    endpoint_registry: EndpointRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    ac_test_registry: ACTestRegistry,
    user_connector_registry: UserConnectorRegistry,
) -> None:
    ldap_register(mode_registry)
    api_register(
        versioned_endpoint_registry=versioned_endpoint_registry,
        endpoint_family_registry=endpoint_family_registry,
    )
    openapi_register(
        endpoint_registry=endpoint_registry,
    )
    ac_test_registry.register(ACTestLDAPSecured)
    ldap_connector.register(user_connector_registry)
