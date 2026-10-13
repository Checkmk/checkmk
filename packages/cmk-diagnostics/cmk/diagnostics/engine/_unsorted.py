#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from cmk.diagnostics.internal import Topic


def topic_id(t: Topic) -> str:
    return "topic_" + re.sub(r"[^a-zA-Z0-9_]", "_", t.localize(str))
