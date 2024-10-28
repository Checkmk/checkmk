#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import toml

# Using `importlib.metadata.version` would be nicer but assumes that we install
# packages as wheels in the site, which we currently don't.
__version__ = toml.load(Path(__file__).parent.parent.parent / "pyproject.toml")["project"][
    "version"
]
