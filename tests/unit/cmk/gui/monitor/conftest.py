#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.paths


@pytest.fixture(name="icon_files")
def fixture_icon_files() -> None:
    """The built-in icons a theme ships and one icon uploaded to the site."""
    theme_images = cmk.utils.paths.web_dir / "htdocs/themes/facelift/images"
    theme_images.mkdir(parents=True, exist_ok=True)
    for name in ("missing", "wiki"):
        (theme_images / f"icon_{name}.svg").write_text("<svg/>")
    uploaded = cmk.utils.paths.local_web_dir / "htdocs/images/icons"
    uploaded.mkdir(parents=True, exist_ok=True)
    (uploaded / "logo.png").write_bytes(b"")
