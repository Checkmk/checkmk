#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This package contains cryptographic functionality for Checkmk.

It aims to provide a coherent, hard-to-misuse API. It should also serve as a facade to both
our crypto dependencies and python's built-in crypto utilities (like hashlib).

Find enclosed:
    cmk.utils.crypto.password_hashing: for creating and validating password hashes

TODO:
    More functionality, hashing, like symmetric and asymmetric cryptography, key derivation,
    randomly generating passwords/UIDs/etc. will be added in the future.
"""
