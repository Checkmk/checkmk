#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
JSON parsing for Kubernetes Pods.

Separate package down a level from from_json, simply so we can split out
pod-specific objects (like container specs and status), to avoid having a single
large "pod.py".
"""
