#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import Secret


class SMTPConnectionParameters(BaseModel):
    tls: bool = False
    port: int | None = None


class BasicAuthParameters(BaseModel):
    username: str
    password: Secret


class SMTPParameters(BaseModel):
    server: str | None = None
    connection: SMTPConnectionParameters
    auth: BasicAuthParameters | None = None


class CommonConnectionParameters(BaseModel):
    disable_tls: bool = False
    disable_cert_validation: bool = False
    port: int | None = None


class Oauth2Parameters(BaseModel):
    client_id: str
    client_secret: Secret
    tenant_id: str


class CommonParameters(BaseModel):
    server: str | None = None
    connection: CommonConnectionParameters
    auth: tuple[Literal["basic"], BasicAuthParameters] | tuple[Literal["oauth2"], Oauth2Parameters]
    email_address: str | None = None


SendingParameters = tuple[Literal["SMTP"], SMTPParameters] | tuple[Literal["EWS"], CommonParameters]

FetchingParameters = tuple[Literal["IMAP", "POP3", "EWS"], CommonParameters]
