#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

import datetime as dt
from typing import Annotated, Literal, Self

from dateutil.relativedelta import relativedelta
from pydantic import AwareDatetime, FutureDatetime

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.framework.model.converter import (
    HostConverter,
    TypedPlainValidator,
)
from cmk.gui.token_auth import AgentRegistrationToken, AuthToken
from cmk.gui.watolib.hosts_and_folders import Host


@api_model
class AgentRegistrationTokenMetadata:
    comment: str = api_field(description="Internal comment for the token. Not displayed to users.")
    issued_at: Annotated[dt.datetime, AwareDatetime] = api_field(
        description="The date and time when the token was issued.",
        example="2024-01-01T00:00:00Z",
    )
    expires_at: Annotated[dt.datetime, AwareDatetime] | None = api_field(
        description="The date and time when the token will expire.",
        example="2025-12-31T23:59:59Z",
    )
    host_name: AnnotatedHostName = api_field(
        description="Name of an existing host the token was issued for"
    )

    @classmethod
    def from_internal(cls, token: AuthToken) -> Self:
        if not isinstance(token.details, AgentRegistrationToken):
            raise ValueError("Token is not a agent registration token")
        return cls(
            comment=token.details.comment,
            host_name=token.details.host_name,
            issued_at=token.issued_at,
            expires_at=token.valid_until,
        )


@api_model
class AgentRegistrationTokenObjectModel(DomainObjectModel):
    domainType: Literal["agent_registration_token"] = api_field(
        description="The domain type of the object."
    )
    extensions: AgentRegistrationTokenMetadata = api_field(
        description="The metadata of this token."
    )


@api_model
class CreateAgentRegistrationToken:
    comment: str = api_field(description="Internal comment for the token. Not displayed to users.")
    expires_at: Annotated[dt.datetime, AwareDatetime, FutureDatetime] | None = api_field(
        description="The date and time when the token will expire. Defaults to one month from now.",
        example="2025-12-31T23:59:59Z",
        default_factory=lambda: dt.datetime.now(dt.UTC) + relativedelta(months=1),
    )
    host: Annotated[
        Host,
        TypedPlainValidator(str, HostConverter().host),
    ] = api_field(description="The name of the host the token should be issued for")
