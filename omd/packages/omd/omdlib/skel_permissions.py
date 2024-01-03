#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Deal with file owners, permissions and the the skel hierarchy"""


import omdlib

Permissions = dict[str, int]

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
