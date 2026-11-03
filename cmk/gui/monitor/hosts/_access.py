#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

LEGACY_ALL_HOSTS_VIEW_NAME: Final = "allhosts"
ALL_HOSTS_PERMISSION: Final = f"view.{LEGACY_ALL_HOSTS_VIEW_NAME}"
