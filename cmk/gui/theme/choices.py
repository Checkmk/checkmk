#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable
from pathlib import Path

from cmk.utils.paths import local_web_dir, web_dir


def theme_choices(
    base_dirs: Iterable[Path] = (web_dir, local_web_dir),
) -> list[tuple[str, str]]:
    themes = {}

    for base_dir in base_dirs:
        if not base_dir.exists():
            continue

        theme_base_dir = base_dir / "htdocs" / "themes"
        if not theme_base_dir.exists():
            continue

        for theme_dir in theme_base_dir.iterdir():
            meta_file = theme_dir / "theme.json"
            if not meta_file.exists():
                continue

            try:
                theme_meta = json.loads(meta_file.open(encoding="utf-8").read())
            except ValueError:
                # Ignore broken meta files and show the directory name as title
                theme_meta = {
                    "title": theme_dir.name,
                }

            assert isinstance(theme_meta["title"], str)
            themes[theme_dir.name] = theme_meta["title"]

    return sorted(themes.items())
