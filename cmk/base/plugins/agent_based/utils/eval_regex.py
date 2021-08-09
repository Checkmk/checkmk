#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re


def instantiate_regex_pattern_once(pattern, match):
    # this correctly handles \( and \) but not [^)] - sorry
    return re.compile(r"(?<!\\)\(.*?(?<!\\)\)").sub(re.escape(match), pattern, 1)
