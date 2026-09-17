#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Site-relative paths of the files the settings pages write."""

from pathlib import Path

GUI_SETTINGS_REL_PATH = Path("etc/check_mk/multisite.d/wato/global.mk")
OMD_SETTINGS_REL_PATH = Path("etc/omd/global.mk")
SITE_SPECIFIC_SETTINGS_REL_PATH = Path("etc/check_mk/multisite.d/sites.mk")
