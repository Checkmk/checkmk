#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Module for files that are "frozen" during config generation.

These files might be used by more than one component (not only the cores).

THIS IS FAR FROM BEING COMPLETE!
"""

from pathlib import Path
from typing import Final

RELATIVE_PATH_SECRETS: Final = Path("stored_passwords")

RELATIVE_PATH_TRUSTED_CAS: Final = Path("ca-certificates.crt")
