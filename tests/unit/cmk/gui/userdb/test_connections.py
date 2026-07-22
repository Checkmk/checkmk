#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.site import omd_site
from cmk.gui.config import Config
from cmk.gui.userdb import effective_authentication_connections
from cmk.livestatus_client import (
    AuthenticationConnectionEntry,
    SAMLAuthenticationEntry,
    SiteConfiguration,
    SiteConfigurations,
)


def _local_self_site(auth_connections: object) -> SiteConfiguration:
    return SiteConfiguration(
        id=omd_site(),
        alias=f"Local site {omd_site()}",
        socket=("local", None),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix=f"/{omd_site()}/",
        multisiteurl="",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication=None,
        timeout=5,
        user_login=True,
        proxy=None,
        authentication_connections=auth_connections,  # type: ignore[typeddict-item]
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=True,
    )


def test_effective_authentication_connections_on_remote_prefers_propagated_global(
    load_config: Config, remote_site: None
) -> None:
    load_config.sites = SiteConfigurations(
        {omd_site(): _local_self_site(("all", ["ldap", "saml"]))}
    )
    propagated: list[AuthenticationConnectionEntry] = [
        (
            "saml",
            SAMLAuthenticationEntry(
                connection_id="foo",
                acs_endpoint="http://localhost/remote/check_mk/saml_acs.py?acs",
                metadata_endpoint="http://localhost/remote/check_mk/saml_metadata.py?RelayState=foo",
            ),
        )
    ]
    load_config.authentication_connections = propagated

    # The seeded local self-default must not shadow the per-site ACS URL
    # that get_site_globals() propagated into the global.
    assert effective_authentication_connections(load_config.sites[omd_site()]) == propagated


def test_effective_authentication_connections_on_central_uses_own(
    load_config: Config,
) -> None:
    own: list[AuthenticationConnectionEntry] = [("ldap", "ldap_conn")]
    load_config.sites = SiteConfigurations({omd_site(): _local_self_site(own)})
    load_config.authentication_connections = [("ldap", "propagated_but_ignored")]

    assert effective_authentication_connections(load_config.sites[omd_site()]) == own


def test_effective_authentication_connections_on_central_disabled(
    load_config: Config,
) -> None:
    load_config.sites = SiteConfigurations({omd_site(): _local_self_site("disabled")})
    load_config.authentication_connections = [("ldap", "propagated_but_ignored")]

    assert effective_authentication_connections(load_config.sites[omd_site()]) == []
