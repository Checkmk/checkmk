#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import signal
from pathlib import Path
from typing import NewType, Optional

from cmk.utils.store import load_object_from_file

ProcessId = NewType("ProcessId", int)


def pid_from_file(pid_file: Path) -> Optional[ProcessId]:
    """Read a process id from a given pid file"""
    try:
        return ProcessId(int(load_object_from_file(pid_file, default=None)))
    except Exception:
        return None


def send_signal(pid: ProcessId, sig: signal.Signals) -> None:
    """A simple, type safe wrapper around os.kill(int, int)"""
    os.kill(pid, sig)
