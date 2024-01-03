#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import omdlib


class VersionInfo:
    """Provides OMD version/platform specific infos"""

    def __init__(self, version: str) -> None:
        self._version = version

        # Register all relevant vars
        self.USERADD_OPTIONS = ""
        self.APACHE_USER = ""
        self.ADD_USER_TO_GROUP = ""
        self.MOUNT_OPTIONS = ""
        self.INIT_CMD = ""
        self.APACHE_CTL = ""
        self.APACHE_INIT_NAME = ""
        self.OMD_PHYSICAL_BASE = ""
        self.APACHE_CONF_DIR = ""
        self.DISTRO_CODE = ""

    def load(self) -> None:
        """Update vars with real values from info file"""
        for k, v in self._read_info().items():
            setattr(self, k, v)

    def _read_info(self) -> dict[str, str]:
        info: dict[str, str] = {}
        info_dir = Path("/omd", "versions", omdlib.__version__, "share", "omd")
        for f in info_dir.iterdir():
            if f.suffix == ".info":
                with f.open() as opened_file:
                    for line in opened_file:
                        try:
                            line = line.strip()
                            # Skip comment and empty lines
                            if line.startswith("#") or line == "":
                                continue
                            # Remove everything after the first comment sign
                            if "#" in line:
                                line = line[: line.index("#")].strip()
                            var, value = line.split("=")
                            value = value.strip()
                            if var.endswith("+"):
                                var = var[:-1]  # remove +
                                info[var.strip()] += " " + value
                            else:
                                info[var.strip()] = value
                        except Exception:
                            raise Exception(
                                f'Unable to parse line "{line}" in file "{info_dir / f}"'
                            )
        return info
