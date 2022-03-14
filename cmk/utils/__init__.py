#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Kept for compatibility. Clean up call sites.
# Or even better: move the functions from misc to a better place
from cmk.utils.misc import cachefile_age, key_config_paths, pnp_cleanup, quote_shell_string
