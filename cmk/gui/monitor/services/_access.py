#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

LEGACY_HOST_VIEW_NAME: Final = "host"
HOST_SERVICES_PERMISSION: Final = f"view.{LEGACY_HOST_VIEW_NAME}"
