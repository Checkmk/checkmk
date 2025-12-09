#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

import datetime as dt
from typing import Annotated, Literal, Self

from dateutil.relativedelta import relativedelta
from pydantic import AfterValidator, AwareDatetime, FutureDatetime

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel
from cmk.gui.token_auth import AuthToken, DashboardToken
from cmk.gui.type_defs import AnnotatedUserId


@api_model
class DashboardTokenMetadata:
    is_disabled: bool = api_field(description="Indicates whether the token is disabled.")
    comment: str = api_field(description="Internal comment for the token. Not displayed to users.")
    issued_at: Annotated[dt.datetime, AwareDatetime] = api_field(
        description="The date and time when the token was issued.",
        example="2024-01-01T00:00:00Z",
    )
    expires_at: Annotated[dt.datetime, AwareDatetime] | None = api_field(
        description="The date and time when the token will expire.",
        example="2025-12-31T23:59:59Z",
    )

    @classmethod
    def from_internal(cls, token: AuthToken) -> Self:
        if not isinstance(token.details, DashboardToken):
            raise ValueError("Token is not a dashboard token")
        return cls(
            is_disabled=token.details.disabled,
            comment=token.details.comment,
            issued_at=token.issued_at,
            expires_at=token.valid_until,
        )


@api_model
class DashboardTokenModel(DashboardTokenMetadata):
    token_id: str = api_field(description="The unique identifier of the dashboard token.")

    @classmethod
    def from_internal(cls, token: AuthToken) -> Self:
        base = DashboardTokenMetadata.from_internal(token)
        return cls(
            token_id=token.token_id,
            is_disabled=base.is_disabled,
            comment=base.comment,
            issued_at=base.issued_at,
            expires_at=base.expires_at,
        )


@api_model
class DashboardTokenObjectModel(DomainObjectModel):
    domainType: Literal["dashboard_token"] = api_field(description="The domain type of the object.")
    extensions: DashboardTokenMetadata = api_field(description="The metadata of this token.")


def _validate_max_time(value: dt.datetime) -> dt.datetime:
    now = dt.datetime.now(dt.UTC)
    if value >= (now + relativedelta(years=2)):
        raise ValueError("Expiration time must be less than two years from now.")
    return value


@api_model
class _BaseDashboardTokenRequest:
    dashboard_owner: AnnotatedUserId = api_field(description="The user ID of the dashboard owner.")
    dashboard_id: str = api_field(
        description="The ID of the dashboard for which the token is being created."
    )


@api_model
class _BaseDashboardTokenRequestWithComment(_BaseDashboardTokenRequest):
    comment: str = api_field(description="Internal comment for the token. Not displayed to users.")


@api_model
class CreateDashboardToken(_BaseDashboardTokenRequestWithComment):
    expires_at: Annotated[
        dt.datetime, AwareDatetime, FutureDatetime, AfterValidator(_validate_max_time)
    ] = api_field(
        description="The date and time when the token will expire. Defaults to one year from now.",
        example="2025-12-31T23:59:59Z",
        default_factory=lambda: dt.datetime.now(dt.UTC) + relativedelta(years=1),
    )


@api_model
class EditDashboardToken(_BaseDashboardTokenRequestWithComment):
    is_disabled: bool = api_field(description="Indicates whether the token is disabled.")
    # NOTE: We don't use FutureDatetime here since the token may already be expired
    # TODO: do we even want to allow editing the expiration time
    expires_at: Annotated[dt.datetime, AwareDatetime, AfterValidator(_validate_max_time)] = (
        api_field(
            description="The date and time when the token will expire.",
            example="2025-12-31T23:59:59Z",
        )
    )


@api_model
class DeleteDashboardToken(_BaseDashboardTokenRequest):
    pass
