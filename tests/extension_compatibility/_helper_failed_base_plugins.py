#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.utils import paths

from cmk.base.check_api import get_check_api_context
from cmk.base.config import load_all_plugins

print(
    json.dumps(
        load_all_plugins(
            get_check_api_context,
            local_checks_dir=paths.local_checks_dir,
            checks_dir=paths.checks_dir,
        )
    )
)
