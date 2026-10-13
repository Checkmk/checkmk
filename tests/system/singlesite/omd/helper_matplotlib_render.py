#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt

output_path = os.path.join(os.environ["OMD_ROOT"], sys.argv[1])

fig, ax = plt.subplots()
if output_path.endswith(".svg"):
    ax.bar(["a", "b", "c"], [1, 2, 3])
else:
    ax.plot([0, 1, 2, 3], [0, 1, 4, 9])
fig.savefig(output_path)
