#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import create_environ

from cmk.gui.config import Config
from cmk.gui.http import Request, response
from cmk.gui.oauth.pages._oauth_well_known import OAuthAuthorizationServerMetadataPage
from cmk.gui.pages import PageContext


@pytest.mark.usefixtures("request_context")
class TestOAuthAuthorizationServerMetadataPage:
    def test_returns_metadata_when_enabled(self) -> None:
        OAuthAuthorizationServerMetadataPage(lambda: True).handle_page(
            PageContext(config=Config(), request=Request(create_environ()))
        )

        assert response.status_code == 200
        assert response.json == {
            "issuer": "http://localhost/oauth-NO_SITE",
            "authorization_endpoint": "http://localhost/oauth-NO_SITE/authorize",
            "registration_endpoint": "http://localhost/oauth-NO_SITE/register",
            "token_endpoint": "http://localhost/oauth-NO_SITE/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"],
        }

    def test_returns_404_when_disabled(self) -> None:
        OAuthAuthorizationServerMetadataPage(lambda: False).handle_page(
            PageContext(config=Config(), request=Request(create_environ()))
        )

        assert response.status_code == 404
