#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.logged_in import user


def search(*args, **kw):
    return {
        "userName": user.id,
        "email": user.email,
        "roles": user.role_ids,
        "extensions": {
            "language": user.language,
            "contact_groups": user.contact_groups,
        },
    }
