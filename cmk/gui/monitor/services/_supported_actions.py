#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What every page that offers a service may do with it."""

from cmk.shared_typing.monitoring.action_ident import ServiceActionIdent

# The shared types declare the service commands, so the frontend can tell it implements them all.
SERVICE_SUPPORTED_ACTIONS: tuple[ServiceActionIdent, ...] = tuple(ServiceActionIdent)
