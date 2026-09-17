#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.oauth.pages._authorize import OAuthAuthorizePage
from cmk.gui.oauth.pages._client_registration import OAuthClientRegistrationPage
from cmk.gui.oauth.pages._introspect import OAuthIntrospectPage
from cmk.gui.oauth.pages._oauth_well_known import OAuthAuthorizationServerMetadataPage
from cmk.gui.oauth.pages._token import OAuthTokenPage
from cmk.gui.oauth.wato._main_module import register as register_main_module
from cmk.gui.oauth.wato._registered_clients_mode import (
    register as register_registered_clients_mode,
)
from cmk.gui.oauth.wato._user_tokens_mode import register as register_user_tokens_mode
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry
from cmk.gui.watolib.mode import ModeRegistry


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    main_module_registry: MainModuleRegistry,
) -> None:
    """Register the OAuth authorization server pages of this site."""

    page_registry.register(
        PageEndpoint("noauth:oauth_authorization_server", OAuthAuthorizationServerMetadataPage())
    )
    page_registry.register(PageEndpoint("oauth_authorize", OAuthAuthorizePage()))
    page_registry.register(
        PageEndpoint("noauth:oauth_client_registration", OAuthClientRegistrationPage())
    )
    page_registry.register(PageEndpoint("noauth:oauth_token", OAuthTokenPage()))
    page_registry.register(PageEndpoint("noauth:oauth_introspect", OAuthIntrospectPage()))
    register_registered_clients_mode(mode_registry)
    register_user_tokens_mode(mode_registry)
    register_main_module(main_module_registry)
