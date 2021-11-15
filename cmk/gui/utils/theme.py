#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

import cmk.utils.paths
from cmk.utils.version import is_managed_edition


class Theme:
    def __init__(self) -> None:
        self._default_theme = "facelift"
        self._theme = "facelift"
        self.theme_choices: List[Tuple[str, str]] = theme_choices()

    def from_config(self, default_theme: str) -> None:
        self._default_theme = default_theme
        self._theme = default_theme

    def set(self, theme_id: str) -> None:
        if not theme_id:
            theme_id = self._default_theme

        if theme_id not in dict(self.theme_choices):
            theme_id = self._default_theme

        self._theme = theme_id

    def get(self) -> str:
        return self._theme

    def icon_themes(self) -> List[str]:
        """Returns the themes where icons of a theme can be found in decreasing order of importance.
        By default the facelift theme provides all icons. If a theme wants to use different icons it
        only needs to add those icons under the same name. See detect_icon_path for a detailed list
        of paths.
        """
        return ["facelift"] if self._theme == "facelift" else [self._theme, "facelift"]

    def detect_icon_path(self, icon_name: str, prefix: str) -> str:
        """Detect from which place an icon shall be used and return it's path relative to htdocs/

        Priority:
        1. In case the modern-dark theme is active: <theme> = modern-dark -> priorities 3-6
        2. In case the modern-dark theme is active: <theme> = facelift -> priorities 3-6
        3. In case a theme is active: themes/<theme>/images/icon_[name].svg in site local hierarchy
        4. In case a theme is active: themes/<theme>/images/icon_[name].svg in standard hierarchy
        5. In case a theme is active: themes/<theme>/images/icon_[name].png in site local hierarchy
        6. In case a theme is active: themes/<theme>/images/icon_[name].png in standard hierarchy
        7. images/icons/[name].png in site local hierarchy
        8. images/icons/[name].png in standard hierarchy
        """
        for theme_id in self.icon_themes():
            if icon_path := self._find_icon_in_dir(
                "themes/%s/images" % theme_id, icon_name, prefix
            ):
                return icon_path

        if icon_path := self._find_icon_in_dir("images/icons", icon_name, prefix=""):
            return icon_path

        return self.detect_icon_path("missing", "icon_")

    def _find_icon_in_dir(self, icon_dir: str, icon_name: str, prefix: str) -> Optional[str]:
        for base_dir in [str(cmk.utils.paths.local_web_dir), cmk.utils.paths.web_dir]:
            for file_type in ["svg", "png"]:
                rel_path = icon_dir + "/" + prefix + icon_name + "." + file_type
                if os.path.exists(base_dir + "/htdocs/" + rel_path):
                    return rel_path

        return None

    def url(self, rel_url: str) -> str:
        return "themes/%s/%s" % (self._theme, rel_url)

    def base_dir(self) -> Path:
        return cmk.utils.paths.local_web_dir / "htdocs" / "themes" / self._theme

    def has_custom_logo(self) -> bool:
        """Whether or not the current CME customer has a custom logo

        CME snapshot sync copies the customer logo to themes/facelift/images/mk-logo.png.
        See CMESnapshotDataCollector._update_customer_sidebar_top.
        """
        return is_managed_edition() and self.base_dir().joinpath("images", "mk-logo.png").exists()


def theme_choices() -> List[Tuple[str, str]]:
    themes = {}

    for base_dir in [Path(cmk.utils.paths.web_dir), cmk.utils.paths.local_web_dir]:
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
