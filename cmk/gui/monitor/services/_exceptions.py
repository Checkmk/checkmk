#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


class ServiceNotFoundError(KeyError):
    """Raised when a service cannot be found by its identifiers."""


class InvalidServiceFilterError(ValueError):
    """Raised when a service filter tree is not one the services listing accepts."""


class HostNotFoundError(LookupError):
    """Raised when the host whose services are asked for does not exist."""
