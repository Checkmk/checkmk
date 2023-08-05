#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.backup import pages as backup
from cmk.gui.pages import PageRegistry
from cmk.gui.watolib.mode import ModeRegistry


def backup_register(page_registry: PageRegistry, mode_registry: ModeRegistry) -> None:
    backup.register(page_registry, mode_registry)
