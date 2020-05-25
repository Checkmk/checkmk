#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module is a little wrapper for the Python 2 subprocess.Popen and
communicate method in order to allow the flag 'encoding' as Python 3 version
does. This can be removed after Python 3 migration.
"""

import sys
import subprocess

PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
list2cmdline = subprocess.list2cmdline
call = subprocess.call
check_output = subprocess.check_output
CalledProcessError = subprocess.CalledProcessError

if sys.platform == "win32":
    CREATE_NEW_PROCESS_GROUP = subprocess.CREATE_NEW_PROCESS_GROUP
else:
    CREATE_NEW_PROCESS_GROUP = None

Popen = subprocess.Popen
