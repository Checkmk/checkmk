#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.config import Config
from cmk.gui.form_specs.generators.age import Age
from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupUserManagement
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Help, Message, Title

_DEFAULTS = Config().oauth_sessions
_MAGNITUDES = [fs.TimeMagnitude.MINUTE, fs.TimeMagnitude.HOUR, fs.TimeMagnitude.DAY]


def _validate_lifetimes(value: Mapping[str, object]) -> None:
    grant_lifetime = value["grant_lifetime"]
    refresh_token_lifetime = value["refresh_token_lifetime"]
    access_token_lifetime = value["access_token_lifetime"]
    assert isinstance(grant_lifetime, int | float)
    assert isinstance(refresh_token_lifetime, int | float)
    assert isinstance(access_token_lifetime, int | float)
    if refresh_token_lifetime > grant_lifetime:
        raise fs.validators.ValidationError(
            Message("The refresh token lifetime must not exceed the session lifetime")
        )
    if access_token_lifetime > refresh_token_lifetime:
        raise fs.validators.ValidationError(
            Message("The access token lifetime must not exceed the refresh token lifetime")
        )


ConfigVariableOAuthSessions = ConfigVariable(
    group=ConfigVariableGroupUserManagement,
    primary_domain=ConfigDomainGUI,
    ident="oauth_sessions",
    form_spec=lambda context: fs.Dictionary(  # noqa: ARG005
        title=Title("OAuth sessions"),
        help_text=Help(
            "Lifetimes of the sessions that OAuth clients, such as MCP clients, "
            "open on behalf of a user. Changes to the session lifetime apply "
            "to sessions created afterwards. The refresh and access token "
            "lifetimes apply to every token issued afterwards, including "
            "refreshes of existing sessions."
        ),
        elements={
            "grant_lifetime": fs.DictElement(
                required=True,
                parameter_form=Age(
                    title=Title("Session lifetime"),
                    displayed_magnitudes=_MAGNITUDES,
                    help_text=Help(
                        "After this time the user has to log in and approve the "
                        "client again, however actively the session is used."
                    ),
                    prefill=fs.DefaultValue(float(_DEFAULTS["grant_lifetime"])),
                    custom_validate=[fs.validators.NumberInRange(min_value=60)],
                ),
            ),
            "refresh_token_lifetime": fs.DictElement(
                required=True,
                parameter_form=Age(
                    title=Title("Refresh token lifetime"),
                    displayed_magnitudes=_MAGNITUDES,
                    help_text=Help(
                        "A refresh token that is not used for this long expires. "
                        "Every refresh issues a new refresh token, so clients in "
                        "active use keep working."
                    ),
                    prefill=fs.DefaultValue(float(_DEFAULTS["refresh_token_lifetime"])),
                    custom_validate=[fs.validators.NumberInRange(min_value=60)],
                ),
            ),
            "access_token_lifetime": fs.DictElement(
                required=True,
                parameter_form=Age(
                    title=Title("Access token lifetime"),
                    displayed_magnitudes=_MAGNITUDES,
                    help_text=Help(
                        "How long a client can call the API with one access token "
                        "before it has to refresh it."
                    ),
                    prefill=fs.DefaultValue(float(_DEFAULTS["access_token_lifetime"])),
                    custom_validate=[fs.validators.NumberInRange(min_value=60)],
                ),
            ),
        },
        custom_validate=[_validate_lifetimes],
    ),
)
