#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The commands every page that offers a host may run on it, in one place."""

from cmk.shared_typing.monitoring.action_ident import HostActionIdent

# The shared types declare the host commands, so the frontend can tell it implements them all.
HOST_SUPPORTED_ACTIONS: tuple[HostActionIdent, ...] = tuple(HostActionIdent)
