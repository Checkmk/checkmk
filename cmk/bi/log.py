#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.log import logger

# TODO: for now it is fine to log everything to the "web.bi.compilation" child, but we may want to
# rework the logging setup in the future, i.e. dedicated log file, logger per module, etc.
LOGGER = logger.getChild("web.bi.compilation")
