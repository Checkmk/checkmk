#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final, Literal

from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.valuespec import Age, Dictionary
from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupUserManagement

_DEFAULTS = Config().oauth_sessions
_MAGNITUDES: Final[tuple[Literal["minutes", "hours", "days"], ...]] = ("minutes", "hours", "days")


def _validate_lifetimes(value: Mapping[str, int], varprefix: str) -> None:
    if value["refresh_token_lifetime"] > value["grant_lifetime"]:
        raise MKUserError(
            varprefix, _("The refresh token lifetime must not exceed the session lifetime")
        )
    if value["access_token_lifetime"] > value["refresh_token_lifetime"]:
        raise MKUserError(
            varprefix, _("The access token lifetime must not exceed the refresh token lifetime")
        )


ConfigVariableOAuthSessions = ConfigVariable(
    group=ConfigVariableGroupUserManagement,
    primary_domain=ConfigDomainGUI,
    ident="oauth_sessions",
    valuespec=lambda context: Dictionary(
        title=_("OAuth sessions"),
        help=_(
            "Lifetimes of the sessions that OAuth clients, such as MCP clients, "
            "open on behalf of a user. Changes to the session lifetime apply "
            "to sessions created afterwards. The refresh and access token "
            "lifetimes apply to every token issued afterwards, including "
            "refreshes of existing sessions."
        ),
        elements=[
            (
                "grant_lifetime",
                Age(
                    title=_("Session lifetime"),
                    display=_MAGNITUDES,
                    minvalue=60,
                    help=_(
                        "After this time the user has to log in and approve the "
                        "client again, however actively the session is used."
                    ),
                    default_value=_DEFAULTS["grant_lifetime"],
                ),
            ),
            (
                "refresh_token_lifetime",
                Age(
                    title=_("Refresh token lifetime"),
                    display=_MAGNITUDES,
                    minvalue=60,
                    help=_(
                        "A refresh token that is not used for this long expires. "
                        "Every refresh issues a new refresh token, so clients in "
                        "active use keep working."
                    ),
                    default_value=_DEFAULTS["refresh_token_lifetime"],
                ),
            ),
            (
                "access_token_lifetime",
                Age(
                    title=_("Access token lifetime"),
                    display=_MAGNITUDES,
                    minvalue=60,
                    help=_(
                        "How long a client can call the API with one access token "
                        "before it has to refresh it."
                    ),
                    default_value=_DEFAULTS["access_token_lifetime"],
                ),
            ),
        ],
        required_keys=["grant_lifetime", "refresh_token_lifetime", "access_token_lifetime"],
        validate=_validate_lifetimes,
    ),
)
