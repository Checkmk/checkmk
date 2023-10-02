#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.fields.utils import BaseSchema

from cmk import fields


class X509PEM(BaseSchema):
    cert = fields.String(
        required=True,
        description="PEM-encoded X.509 certificate.",
    )


class AgentControllerCertificateSettings(BaseSchema):
    lifetime_in_months = fields.Integer(
        description="Lifetime of agent controller certificates in months",
        required=True,
        example=60,
    )
