#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sqlite3
import threading
from collections.abc import Callable

from cmk.gui.oauth.store.backend import initialize_database, oauth_db_path, open_connection
from cmk.gui.oauth.store.client_store import ClientStore
from cmk.gui.oauth.store.token_store import looks_like_token, TokenStore
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.watolib.main_menu import MainModuleRegistry
from cmk.gui.watolib.mode import ModeRegistry

__all__ = ["register", "client_store", "token_store", "looks_like_token"]


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    main_module_registry: MainModuleRegistry,
    *,
    enabled: Callable[[], bool],
) -> None:
    """Register the OAuth authorization server pages of this site.

    enabled decides whether any OAuth-consuming feature (currently only the
    MCP server) is active for the site; while it returns False, every page
    answers 404.

    The Setup page for managing already-registered clients is always
    available, independent of enabled -- an admin may still need to review
    or delete registered clients after disabling the feature.

    The page/mode/main-module imports are deferred to here rather than living
    at module level: they pull in cmk.gui.wato, and cmk.gui.auth imports this
    module at module level for token_store(), so importing them eagerly would
    reintroduce the auth -> oauth -> wato -> auth cycle.
    """
    from cmk.gui.oauth._authorization_server import OAuthAuthorizationServerMetadataPage
    from cmk.gui.oauth._authorize import OAuthAuthorizePage
    from cmk.gui.oauth._client_registration import OAuthClientRegistrationPage
    from cmk.gui.oauth._main_module import register as register_main_module
    from cmk.gui.oauth._registered_clients_mode import (
        register as register_registered_clients_mode,
    )
    from cmk.gui.oauth._token import OAuthTokenPage

    page_registry.register(
        PageEndpoint(
            "noauth:oauth_authorization_server", OAuthAuthorizationServerMetadataPage(enabled)
        )
    )
    page_registry.register(PageEndpoint("oauth_authorize", OAuthAuthorizePage(enabled)))
    page_registry.register(
        PageEndpoint("noauth:oauth_client_registration", OAuthClientRegistrationPage(enabled))
    )
    page_registry.register(PageEndpoint("noauth:oauth_token", OAuthTokenPage(enabled)))
    register_registered_clients_mode(mode_registry)
    register_main_module(main_module_registry)


# The OAuth stores share one sqlite connection per worker process: opened on
# first use, reused for the rest of the process's lifetime, never closed.
_connection_lock = threading.Lock()
_connection: sqlite3.Connection | None = None


def _get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        # The lock only guards against a first-use race between threads.
        with _connection_lock:
            if _connection is None:
                db_path = oauth_db_path()
                initialize_database(db_path)
                _connection = open_connection(db_path)
    return _connection


def token_store() -> TokenStore:
    """Get the token store, backed by the shared per-process connection."""
    return TokenStore(_get_connection())


def client_store() -> ClientStore:
    """Get the registered-client store, backed by the shared per-process connection."""
    return ClientStore(_get_connection())
