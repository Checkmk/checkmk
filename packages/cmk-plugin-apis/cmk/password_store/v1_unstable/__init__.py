#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
WARNING
-------

**This version of the API is work in progress and not yet stable.
It is not recommended to use this version in production systems.**

**However: we do intend to stabilize this API version in the future and release it,
so you are encouraged to experiment and give us feedback.**


Scope
-----

This API provides functionality to be used by server-side programs
running on the Checkmk server.
It is written with special agents and active checks in mind -- we do
not guarantee they work in other circumstances.

This is the first version of the password store API.

"""

from ._convenience import parser_add_secret_option, resolve_secret_option
from ._impl import dereference_secret, get_store_secret, PasswordStore, PasswordStoreError, Secret

# order is reflected in sphinx doc.
__all__ = [
    "Secret",
    "parser_add_secret_option",
    "resolve_secret_option",
    "dereference_secret",
    "PasswordStoreError",
    "PasswordStore",
    "get_store_secret",
]
