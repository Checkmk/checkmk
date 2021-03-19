#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

__all__ = ["VERBOSE"]

# Just for reference, the predefined logging levels:
#
# syslog/CMC    Python         added to Python
# --------------------------------------------
# emerg  0
# alert  1
# crit   2      CRITICAL 50
# err    3      ERROR    40
# warn   4      WARNING  30                 <= default level in Python
# notice 5                                  <= default level in CMC
# info   6      INFO     20
#                              VERBOSE  15
# debug  7      DEBUG    10
#
# NOTE: VERBOSE is a bit confusing and suffers from the not-invented-here
# syndrome. If we really insist on 3 verbosity levels (normal, verbose, very
# verbose), we should probably do the following:
#
#    * Nuke VERBOSE.
#    * Introduce NOTICE (25).
#    * Make NOTICE the default level.
#    * Optionally introduce EMERGENCY (70) and ALERT (60) for consistency.
#
# This would make our whole logging story much more consistent internally
# (code) and externally (GUI always offers the same levels). Nevertheless, we
# should keep in mind that the Python documentation strongly discourages
# introducing new log levels, at least for libraries. OTOH, with 3 verbosity
# levels, this would force us to log normal stuff with a WARNING level, which
# looks wrong.

# We need an additional log level between INFO and DEBUG to reflect the
# verbose() and vverbose() mechanisms of Checkmk.
VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")
