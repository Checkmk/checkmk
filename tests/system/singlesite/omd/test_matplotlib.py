#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# matplotlib (CMK-35581) is wired into the build ahead of any actual usage. These are smoke tests
# for that wiring, not for cmk-graphing-engine code: they confirm the package actually shipped with
# the site -- built with its vendored freetype/harfbuzz/sheenbidi/libraqm/qhull, see
# omd/packages/python3-modules/build-python3-modules.bzl -- is importable and can render a plot.

from tests.testlib.site import Site

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_matplotlib_is_importable(site: Site) -> None:
    assert site.check_output(
        ["python3", "-c", "import matplotlib; print(matplotlib.__version__)"]
    ).strip()


def test_pyplot_renders_a_line_plot_to_png(site: Site) -> None:
    with site.python_helper("helper_matplotlib_render.py").execute(
        args=["test_matplotlib.png"]
    ) as p:
        assert p.wait() == 0
    try:
        assert site.read_file("test_matplotlib.png", encoding=None).startswith(_PNG_MAGIC)
    finally:
        site.delete_file("test_matplotlib.png")


def test_pyplot_renders_a_svg_with_expected_element(site: Site) -> None:
    with site.python_helper("helper_matplotlib_render.py").execute(
        args=["test_matplotlib.svg"]
    ) as p:
        assert p.wait() == 0
    try:
        assert "<svg" in site.read_file("test_matplotlib.svg")
    finally:
        site.delete_file("test_matplotlib.svg")
