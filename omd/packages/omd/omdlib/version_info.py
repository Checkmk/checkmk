#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
#       U  ___ u  __  __   ____
#        \/"_ \/U|' \/ '|u|  _"\
#        | | | |\| |\/| |/| | | |
#    .-,_| |_| | | |  | |U| |_| |\
#     \_)-\___/  |_|  |_| |____/ u
#          \\   <<,-,,-.   |||_
#         (__)   (./  \.) (__)_)
#
# This file is part of OMD - The Open Monitoring Distribution.
# The official homepage is at <http://omdistro.org>.
#
# OMD  is  free software;  you  can  redistribute it  and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the  Free Software  Foundation  in  version 2.  OMD  is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.


from pathlib import Path
from typing import Dict

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

    def _read_info(self) -> Dict[str, str]:
        info: Dict[str, str] = {}
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
                                'Unable to parse line "%s" in file "%s"' % (line, info_dir / f)
                            )
        return info
