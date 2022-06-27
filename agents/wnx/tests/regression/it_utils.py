#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import platform
import subprocess
from typing import Optional, Sequence

import pytest


def check_actual_input(name: str, lines: int, alone: bool, data: Optional[Sequence[str]]) -> bool:
    if data is None:
        pytest.skip(f"Section '{name}': Data is absent")
        return False

    if not alone:
        lines += 2

    if len(data) < lines:
        all_data = "\n".join(data)
        pytest.skip(f"Section '{name}': Data is TOO short:\n{all_data}\n")
        return False

    return True


def safe_binary_remove(binary_path):
    try:
        os.unlink(binary_path)
    except OSError as os_error:
        print("Error %s during file delete" % os_error.errno)


def stop_ohm():
    # stopping all
    subprocess.call("taskkill /F /IM OpenhardwareMonitorCLI.exe")
    subprocess.call("net stop winring0_1_2_0")


def remove_files(target_dir, binaries):
    # removing all
    for f in binaries:
        safe_binary_remove(os.path.join(target_dir, f))


def make_dir(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)


def check_os():
    if platform.system() != "Windows":
        return False

    return True
