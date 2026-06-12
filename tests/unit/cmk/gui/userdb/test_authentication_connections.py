#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit coverage for per-site ``authentication_connections`` resolution (epic CMK-33267).

Pure resolution helpers the login page and SAML runtime depend on; the
end-to-end behaviour lives in
``tests/composition/identity/test_saml_login_distributed.py``.
"""

from typing import cast

import pytest

from livestatus import (
    AuthenticationConnectionEntry,
    SAMLAuthenticationEntry,
    SiteConfiguration,
)

from cmk.ccc.site import SiteId
from cmk.gui.saml2_login import show_saml2_login
from cmk.gui.user_connection_config_types import (
    LDAPUserConnectionConfig,
    SAMLUserConnectionConfig,
)
from cmk.gui.userdb._connections import (
    effective_authentication_connections,
    get_saml_connections_for_current_site,
    resolved_authentication_connections,
)
from cmk.gui.utils.output_funnel import output_funnel
from tests.testlib.gui.web_test_app import SetConfig

_CENTRAL_SITE = SiteId("central")


def _site_config(**overrides: object) -> SiteConfiguration:
    base = {
        "alias": "test",
        "disable_wato": False,
        "disabled": False,
        "id": _CENTRAL_SITE,
        "insecure": False,
        "multisiteurl": "",
        "persist": False,
        "proxy": None,
        "replicate_ec": False,
        "replicate_mkps": False,
        "replication": None,
        "message_broker_port": 5672,
        "status_host": None,
        "timeout": 10,
        "url_prefix": "/central/",
        "user_login": True,
        "is_trusted": True,
    }
    base.update(overrides)
    return cast(SiteConfiguration, base)


def _saml_connection(connection_id: str, *, disabled: bool = False) -> SAMLUserConnectionConfig:
    return cast(
        SAMLUserConnectionConfig,
        {
            "type": "saml2",
            "id": connection_id,
            "name": connection_id,
            "disabled": disabled,
        },
    )


def _ldap_connection(connection_id: str, *, disabled: bool = False) -> LDAPUserConnectionConfig:
    return cast(
        LDAPUserConnectionConfig,
        {
            "type": "ldap",
            "id": connection_id,
            "name": connection_id,
            "disabled": disabled,
        },
    )


def _saml_entry(connection_id: str) -> AuthenticationConnectionEntry:
    return ("saml", SAMLAuthenticationEntry(connection_id=connection_id))


class TestEffectiveAuthenticationConnections:
    """`effective_authentication_connections` picks the runtime source per site role.

    On the central site the site's own ``authentication_connections`` decides;
    on a remote it is the value propagated into the global config, because
    ``sites.mk`` is not synchronized to remotes and the local site config is
    only the seeded self-default.
    """

    def test_central_site_uses_its_own_value_not_the_propagated_global(
        self, set_config: SetConfig, request_context: None
    ) -> None:
        per_site = [_saml_entry("per_site_saml")]
        with set_config(authentication_connections=[_saml_entry("global_saml")]):
            assert (
                effective_authentication_connections(
                    _site_config(authentication_connections=per_site)
                )
                == per_site
            )

    def test_remote_site_uses_the_propagated_global(
        self, set_config: SetConfig, request_context: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "cmk.gui.userdb._connections.is_distributed_setup_remote_site", lambda sites: True
        )
        propagated = [_saml_entry("propagated_saml")]
        with set_config(authentication_connections=propagated):
            assert (
                effective_authentication_connections(
                    _site_config(authentication_connections=[_saml_entry("seeded_self_default")])
                )
                == propagated
            )

    def test_remote_site_without_propagated_value_resolves_to_empty_list(
        self, set_config: SetConfig, request_context: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "cmk.gui.userdb._connections.is_distributed_setup_remote_site", lambda sites: True
        )
        with set_config(authentication_connections=None):
            assert effective_authentication_connections(_site_config()) == []

    def test_explicitly_disabled_site_authenticates_against_nothing(
        self, set_config: SetConfig, request_context: None
    ) -> None:
        with set_config(user_connections=[_ldap_connection("my_ldap")]):
            assert (
                effective_authentication_connections(
                    _site_config(authentication_connections="disabled")
                )
                == []
            )


class TestResolvedAuthenticationConnections:
    """`resolved_authentication_connections` fixes each site's list on the central for propagation.

    An explicit list (including an empty one) is kept verbatim, so no
    connection registry is consulted; ``"disabled"`` yields nothing; and an
    absent key — only code-constructed specs omit it — falls back to every
    available connection rather than to another site's value.
    """

    def test_explicit_value_passes_through_unexpanded(self) -> None:
        per_site = [_saml_entry("per_site_saml")]
        assert (
            resolved_authentication_connections(
                _site_config(authentication_connections=per_site),
            )
            == per_site
        )

    def test_explicit_empty_value_is_kept(self) -> None:
        """An emptied list means "no connections", not "fall back to the default"."""
        assert (
            resolved_authentication_connections(_site_config(authentication_connections=[])) == []
        )

    def test_disabled_resolves_to_empty_list(self) -> None:
        assert (
            resolved_authentication_connections(_site_config(authentication_connections="disabled"))
            == []
        )

    def test_absent_key_falls_back_to_all_available_connections(
        self, set_config: SetConfig, request_context: None
    ) -> None:
        with set_config(user_connections=[_ldap_connection("my_ldap")]):
            assert resolved_authentication_connections(_site_config()) == [("ldap", "my_ldap")]


class TestGetSamlConnectionsForCurrentSite:
    """`get_saml_connections_for_current_site` returns the site's referenced enabled SAML connections."""

    @pytest.fixture(autouse=True)
    def _on_central_site(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cmk.gui.userdb._connections.omd_site", lambda: _CENTRAL_SITE)

    def test_empty_when_site_has_no_saml_entries(
        self, set_config: SetConfig, request_context: None
    ) -> None:
        with set_config(
            sites={_CENTRAL_SITE: _site_config(authentication_connections=[])},
            user_connections=[_saml_connection("my_saml")],
        ):
            assert get_saml_connections_for_current_site() == {}

    def test_returns_referenced_enabled_saml_connection(
        self, set_config: SetConfig, request_context: None
    ) -> None:
        saml = _saml_connection("my_saml")
        with set_config(
            sites={
                _CENTRAL_SITE: _site_config(authentication_connections=[_saml_entry("my_saml")])
            },
            user_connections=[saml],
        ):
            assert get_saml_connections_for_current_site() == {"my_saml": saml}

    def test_disabled_connection_is_not_returned(
        self, set_config: SetConfig, request_context: None
    ) -> None:
        with set_config(
            sites={
                _CENTRAL_SITE: _site_config(authentication_connections=[_saml_entry("my_saml")])
            },
            user_connections=[_saml_connection("my_saml", disabled=True)],
        ):
            assert get_saml_connections_for_current_site() == {}


class TestLoginPageSsoButtonGating:
    """A globally-configured SAML connection the site does not advertise must not surface on the login page.

    ``login.py`` renders an SSO button per entry from
    ``get_saml_connections_for_current_site()`` via ``show_saml2_login``; an
    empty per-site list yields no buttons while local ``cmkadmin`` login stays.
    """

    @pytest.fixture(autouse=True)
    def _on_central_site(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cmk.gui.userdb._connections.omd_site", lambda: _CENTRAL_SITE)

    def test_login_page_renders_no_sso_button_when_no_connections(
        self, request_context: None
    ) -> None:
        with output_funnel.plugged():
            show_saml2_login([], None, "index.py")
            rendered = "".join(output_funnel.drain())

        assert "_saml2_login_button" not in rendered
        assert "login_separator" not in rendered

    def test_login_page_renders_sso_button_for_assigned_connection(
        self, request_context: None
    ) -> None:
        saml = _saml_connection("my_saml")

        with output_funnel.plugged():
            show_saml2_login([saml], None, "index.py")
            rendered = "".join(output_funnel.drain())

        assert "_saml2_login_button" in rendered
        assert "my_saml" in rendered
