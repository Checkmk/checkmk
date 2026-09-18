#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.rulesets.v1.form_specs import MultilineText


@dataclass(frozen=True, kw_only=True)
class CACertificate(MultilineText):
    """A PEM encoded CA certificate or certificate chain.

    Renders a text area which can also be filled by uploading a file or by
    fetching the certificate from a server.
    """
