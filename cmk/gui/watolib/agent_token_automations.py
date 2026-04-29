#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Automations that issue agent download / registration tokens on a remote site.

Token stores are per-site (`paths.var_dir / "token.store"`) and are not replicated.
For hosts monitored by remote sites the central GUI forwards the token creation
to the redeeming site via `do_remote_automation`; the resulting token is stored
where it will later be redeemed.
"""

import datetime as dt
from typing import Annotated, Self

from dateutil.relativedelta import relativedelta
from pydantic import AwareDatetime, BaseModel, PlainValidator

from livestatus import SiteConfiguration

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.token_auth import (
    AgentDownloadToken,
    AgentRegistrationToken,
    AuthToken,
    get_token_store,
)
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
    MKAutomationException,
    remote_automation_config_from_site_config,
)
from cmk.utils.agent_registration import HostAgentConnectionMode

_AnnotatedUserId = Annotated[UserId, PlainValidator(UserId.parse)]
_AnnotatedHostName = Annotated[HostName, PlainValidator(HostName.parse)]


class AgentDownloadTokenCreateRequest(BaseModel):
    issuer: _AnnotatedUserId
    expires_at: AwareDatetime | None = None


class AgentRegistrationTokenCreateRequest(BaseModel):
    issuer: _AnnotatedUserId
    host_name: _AnnotatedHostName
    connection_mode: HostAgentConnectionMode
    expires_at: AwareDatetime | None = None
    comment: str = ""


class TokenCreateResponse(BaseModel):
    """Wire format returned by the token-create automations to the central site."""

    id: str
    issued_at: AwareDatetime
    expires_at: AwareDatetime | None = None

    @classmethod
    def from_token(cls, token: AuthToken) -> Self:
        return cls(
            id=str(token.token_id),
            issued_at=token.issued_at,
            expires_at=token.valid_until,
        )


class AutomationAgentDownloadTokenCreate(AutomationCommand[AgentDownloadTokenCreateRequest]):
    def command_name(self) -> str:
        return "agent-download-token-create"

    def get_request(self, config: Config, request: Request) -> AgentDownloadTokenCreateRequest:
        return AgentDownloadTokenCreateRequest.model_validate_json(
            request.get_str_input_mandatory("request")
        )

    def execute(self, api_request: AgentDownloadTokenCreateRequest) -> dict[str, object]:
        now = dt.datetime.now(dt.UTC)
        token = get_token_store().issue(
            AgentDownloadToken(),
            issuer=api_request.issuer,
            now=now,
            valid_for=(
                relativedelta(api_request.expires_at, now)
                if api_request.expires_at is not None
                else None
            ),
        )
        return TokenCreateResponse.from_token(token).model_dump(mode="json")


class AutomationAgentRegistrationTokenCreate(
    AutomationCommand[AgentRegistrationTokenCreateRequest]
):
    def command_name(self) -> str:
        return "agent-registration-token-create"

    def get_request(self, config: Config, request: Request) -> AgentRegistrationTokenCreateRequest:
        return AgentRegistrationTokenCreateRequest.model_validate_json(
            request.get_str_input_mandatory("request")
        )

    def execute(self, api_request: AgentRegistrationTokenCreateRequest) -> dict[str, object]:
        now = dt.datetime.now(dt.UTC)
        token = get_token_store().issue(
            AgentRegistrationToken(
                comment=api_request.comment,
                host_name=api_request.host_name,
                connection_mode=api_request.connection_mode,
            ),
            issuer=api_request.issuer,
            now=now,
            valid_for=(
                relativedelta(api_request.expires_at, now)
                if api_request.expires_at is not None
                else None
            ),
        )
        return TokenCreateResponse.from_token(token).model_dump(mode="json")


def forward_token_create(
    *,
    site_id: SiteId,
    site_config: SiteConfiguration,
    command: str,
    request_payload: BaseModel,
    debug: bool,
) -> TokenCreateResponse:
    """Forward a token-create automation to a remote site.

    Raises ``ProblemException(502)`` if the remote site is unreachable, not
    logged in, or replication is disabled.
    """
    try:
        raw = do_remote_automation(
            automation_config=remote_automation_config_from_site_config(site_config),
            command=command,
            vars_=[("request", request_payload.model_dump_json())],
            debug=debug,
        )
    except (MKAutomationException, MKGeneralException) as exc:
        raise ProblemException(
            status=502,
            title="Could not create token on remote site",
            detail=_(
                'Token creation on site "%s" failed: %s. Make sure the central site '
                "is logged into the remote site (Distributed monitoring → Login)."
            )
            % (site_id, exc),
        )
    return TokenCreateResponse.model_validate(raw)
