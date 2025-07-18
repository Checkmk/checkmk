#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc import version
from cmk.utils import paths

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)
