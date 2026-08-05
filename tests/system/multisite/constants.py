#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.crypto.password import Password

# Note: Constants and provided test files must match
TEST_HOST_1 = "au_test_1"
TEST_HOST_2 = "au_test_2"
TEST_CACHE_DIR = "."
SIGNATURE_KEY_ID = 1
SIGNATURE_KEY_NAME = "mykey"
SIGNATURE_KEY_PASSPHRASE = Password("123123123123")
SERVER_REL_MULTISITED_DIR = Path("etc", "check_mk", "multisite.d", "wato")
DUMMY_TEXT = "dummy"
