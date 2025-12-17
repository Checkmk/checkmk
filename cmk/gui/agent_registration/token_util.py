#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import datetime as dt
from collections.abc import Generator

from dateutil.relativedelta import relativedelta
from pydantic_core import ErrorDetails

from cmk.ccc.user import UserId
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.openapi.restful_objects.validators import RequestDataValidator
from cmk.gui.session import UserContext
from cmk.gui.token_auth import AgentRegistrationToken, AuthToken, get_token_store, TokenStore
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.hosts_and_folders import Host


class ImpersonatedAgentRegistrationTokenIssuer:
    """Context for impersonating the issuer of a agent registration token.

    **DO NOT** construct this class directly, instead use the `impersonate_agent_registration_token_issuer`
    context manager.
    """

    def __init__(
        self, token_details: AgentRegistrationToken, user_permissions: UserPermissions
    ) -> None:
        self._token_details = token_details
        self._user_permissions = user_permissions
        self.__invalidated: bool = False

    def invalidate(self) -> None:
        """Invalidate this context, preventing further use."""
        self.__invalidated = True

    def _check_valid(self) -> None:
        """Ensure the impersonation context is still valid."""
        if self.__invalidated:
            raise Exception("Impersonation context has already been exited.")


@contextlib.contextmanager
def impersonate_agent_registration_token_issuer(
    token_issuer: UserId, token_details: AgentRegistrationToken, user_permissions: UserPermissions
) -> Generator[ImpersonatedAgentRegistrationTokenIssuer]:
    """Impersonate the token issuer for the duration of the context.

    The context yields an object which can be used to load user specific data."""
    with UserContext(token_issuer, user_permissions):
        issuer = ImpersonatedAgentRegistrationTokenIssuer(token_details, user_permissions)
        try:
            yield issuer
        finally:
            issuer.invalidate()


def issue_agent_registration_token(
    expiration_time: dt.datetime | None,
    host: Host,
    comment: str = "",
    token_store: TokenStore | None = None,
) -> AuthToken:
    """Issues a new agent registration token."""
    if token_store is None:
        token_store = get_token_store()
    now = dt.datetime.now(dt.UTC)
    if expiration_time is not None and expiration_time <= now:
        raise RequestDataValidator.format_error_details(
            [
                ErrorDetails(
                    type="value_error",
                    msg=_("The expiration time must be in the future."),
                    loc=("body", "expires_at"),
                    input=expiration_time.isoformat(),
                )
            ]
        ) from None
    return token_store.issue(
        AgentRegistrationToken(comment=comment, host_name=host.name()),
        issuer=user.ident,
        now=now,
        valid_for=relativedelta(expiration_time, now) if expiration_time else None,
    )
