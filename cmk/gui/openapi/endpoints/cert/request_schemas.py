#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui import fields as gui_fields
from cmk.gui.fields.utils import BaseSchema


class X509ReqPEMUUID(BaseSchema):
    csr = gui_fields.X509ReqPEMFieldUUID(
        required=True,
        example="-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----\n",
        description="PEM-encoded X.509 CSR. The CN must a valid version-4 UUID.",
    )
