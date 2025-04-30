#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple, override

from cmk.ccc.plugin_registry import Registry


class CertificateInfo(NamedTuple):
    topic: str
    # This should be a callback function because new certificates may be added or removed
    # after the initial registration. For example, in the case of custom SAML certificates,
    # their paths are based on the connection name, which can change.
    # The function should return a dictionary in the format: {<path to cert>: <purpose>}
    get_certs: Callable[[], dict[Path, str]]


class CertInfoRegistry(Registry[CertificateInfo]):
    @override
    def plugin_name(self, instance: CertificateInfo) -> str:
        return instance.topic


cert_info_registry = CertInfoRegistry()
