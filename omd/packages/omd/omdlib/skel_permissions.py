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
"""Deal with file owners, permissions and the the skel hierarchy"""

from typing import Dict

import omdlib

Permissions = Dict[str, int]

_skel_permissions: Permissions = {}


def read_skel_permissions() -> Permissions:
    """Returns a permission map for the skel files
    This runtime cache is important, because the function is called very often while processing
    the skel hierarchy."""
    global _skel_permissions
    if _skel_permissions:
        return _skel_permissions

    _skel_permissions = load_skel_permissions(omdlib.__version__)
    if not _skel_permissions:
        raise Exception(
            "%s is missing or currupted." % skel_permissions_file_path(omdlib.__version__)
        )
    return _skel_permissions


def load_skel_permissions(version: str) -> Permissions:
    return load_skel_permissions_from(skel_permissions_file_path(version))


def load_skel_permissions_from(path: str) -> Permissions:
    perms: Permissions = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line == "" or line[0] == "#":
                continue
            path, perm = line.split()
            mode = int(perm, 8)
            perms[path] = mode
        return perms


def skel_permissions_file_path(version: str) -> str:
    return "/omd/versions/%s/share/omd/skel.permissions" % version
