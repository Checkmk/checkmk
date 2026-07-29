#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# matplotlib (CMK-35581) is wired into the build ahead of any actual usage. These are smoke tests
# for that wiring, not for cmk-graphing-engine code: they confirm the dependency is importable and
# can render a plot in the headless test environment.

import io

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_matplotlib_is_importable() -> None:
    assert matplotlib.__version__


def test_pyplot_renders_a_line_plot_to_png() -> None:
    fig, ax = plt.subplots()
    try:
        ax.plot([0, 1, 2, 3], [0, 1, 4, 9])

        buf = io.BytesIO()
        fig.savefig(buf, format="png")

        assert buf.getvalue().startswith(_PNG_MAGIC)
    finally:
        plt.close(fig)


def test_pyplot_renders_a_svg_with_expected_element() -> None:
    fig, ax = plt.subplots()
    try:
        ax.bar(["a", "b", "c"], [1, 2, 3])

        buf = io.StringIO()
        fig.savefig(buf, format="svg")

        assert "<svg" in buf.getvalue()
    finally:
        plt.close(fig)
