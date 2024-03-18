#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Deal with file owners, permissions and the the skel hierarchy"""

import os

Permissions = dict[str, int]


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


def get_skel_permissions(skel_path: str, perms: Permissions, relpath: str) -> int:
    try:
        return perms[relpath]
    except KeyError:
        if os.path.isdir(f"{skel_path}/{relpath}"):
            return 0o750
        return 0o640
