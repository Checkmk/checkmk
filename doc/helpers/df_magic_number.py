#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import division
normsize = 20.0

import sys
if len(sys.argv) > 1:
    normsize = float(sys.argv[1])


def print_levels(level, exp):
    sys.stdout.write("f=%3.1f: " % exp)
    for size in [5, 10, 20, 50, 100, 300, 800]:
        hgb_size = size / normsize  # fixed: true-division
        felt_size = hgb_size**exp
        scale = felt_size / hgb_size  # fixed: true-division
        new_level = 1 - ((1 - level) * scale)
        freegb = size * (1.0 - new_level)
        sys.stdout.write("%4.0fGB:%4.0f%%(%3.0fG) " % (size, new_level * 100, freegb))
    sys.stdout.write("\n")


for level in [.80, .85, .90, .95]:
    sys.stdout.write("Level for %.0f GB Normpartition: %d%%\n" % (normsize, int(level * 100)))
    for exp in [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]:
        print_levels(level, exp)
    sys.stdout.write("-" * 80)
    sys.stdout.write("\n")
