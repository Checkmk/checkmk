#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


class SiteInfoInvalidError(Exception):
    pass


class SiteInfoItemsInvalidError(Exception):
    pass


class NoServicesInfoError(Exception):
    pass


class ServicesInfoLengthError(Exception):
    pass


class InvalidTelemetryEndpointError(Exception):
    pass


class InvalidTimestampError(Exception):
    pass


class TelemetryConfigError(Exception):
    pass
