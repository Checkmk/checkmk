#!/usr/bin/env python3
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
from uuid import uuid4

from omdlib.contexts import SiteContext


def has_instance_id(site: SiteContext) -> bool:
    return _get_instance_id_filepath(site).exists()


def save_instance_id(site: SiteContext) -> None:
    instance_id_filepath = _get_instance_id_filepath(site)
    instance_id_filepath.parent.mkdir(parents=True, exist_ok=True)
    with instance_id_filepath.open("w", encoding="utf-8") as f:
        f.write(str(uuid4()))


def _get_instance_id_filepath(site: SiteContext) -> Path:
    return Path(site.dir, "etc/omd/instance_id")
