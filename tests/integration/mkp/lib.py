#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

from tests.testlib.site import Site


def add_extension(site: Site, path: Path) -> None:
    site.check_output(["mkp", "add", path.as_posix()])


def enable_extension(site: Site, name: str) -> None:
    site.check_output(["mkp", "enable", name])


def disable_extension(site: Site, name: str) -> None:
    site.check_output(["mkp", "disable", name])


def remove_extension(site: Site, name: str) -> None:
    site.check_output(["mkp", "remove", name])
