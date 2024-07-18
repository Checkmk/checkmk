#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Wrapper for pika connection classes"""
import subprocess


def get_local_port() -> int:
    """Get the port of the local messaging broker"""
    return int(subprocess.check_output(["omd", "config", "show", "RABBITMQ_PORT"]))
