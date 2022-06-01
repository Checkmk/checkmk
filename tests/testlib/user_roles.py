#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from typing import Iterator, List

import cmk.gui.config as config
from cmk.gui.watolib.userroles import clone_role, delete_role, RoleID


@contextlib.contextmanager
def create_and_destroy_user_roles(roles_to_clone: List[str]) -> Iterator[List]:
    # Load the config so that superuser's roles are available
    config.load_config()

    cloned_roles = [clone_role(RoleID(rolename)).name for rolename in roles_to_clone]

    yield cloned_roles

    for rolename in cloned_roles:
        delete_role(RoleID(rolename))
