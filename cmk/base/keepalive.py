#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import KeepaliveAPI
from cmk.utils.version import Edition

from cmk.base.no_keepalive import NO_KEEPALIVE


def get_keepalive(edition: Edition) -> KeepaliveAPI:
    if edition is Edition.CRE:
        return NO_KEEPALIVE

    import cmk.base.cee.keepalive as keepalive  # type: ignore[import] # pylint: disable=no-name-in-module

    return keepalive
