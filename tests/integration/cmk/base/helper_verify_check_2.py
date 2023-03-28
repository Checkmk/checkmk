#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths

import cmk.base.check_api as check_api
import cmk.base.config as config

config.load_checks(
    check_api.get_check_api_context,
    [f"{cmk.utils.paths.local_checks_dir}/test_check_2"],
)
config.load(with_conf_d=False)

# Verify that the default variable is in the check context and
# not in the global checks module context
assert "discover_service" not in config.__dict__
assert "test_check_2" in config._check_contexts
assert "discover_service" in config._check_contexts["test_check_2"]
