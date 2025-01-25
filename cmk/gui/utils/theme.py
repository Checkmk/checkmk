#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from pathlib import Path

from cmk.ccc.version import Edition, edition

import cmk.utils.paths

from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.exceptions import MKInternalError
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _


class Theme:
    def __init__(self, validate_choices: bool) -> None:
        self._default_theme = "facelift"
        self._theme = "facelift"
        self.theme_choices: list[tuple[str, str]] = theme_choices()

        if not self.theme_choices and validate_choices:
            raise MKInternalError(_("No valid theme directories found."))

        if self._default_theme not in dict(self.theme_choices) and validate_choices:
            raise MKInternalError(
                _('The default theme "%s" is not given among the found theme choices: %s.')
                % (self._default_theme, self.theme_choices)
            )

    def from_config(self, default_theme: str) -> None:
        # Only set the config default theme if it's part of the theme choices
        if default_theme in dict(self.theme_choices):
            self._default_theme = default_theme
            self._theme = default_theme

    def set(self, theme_id: str | None) -> None:
        if not theme_id:
            theme_id = self._default_theme

        if theme_id not in dict(self.theme_choices):
            theme_id = self._default_theme

        self._theme = theme_id

    def get(self) -> str:
        return self._theme

    def icon_themes(self) -> list[str]:
        """Returns the themes where icons of a theme can be found in decreasing order of importance.
        By default the facelift theme provides all icons. If a theme wants to use different icons it
        only needs to add those icons under the same name. See detect_icon_path for a detailed list
        of paths.
        """
        return ["facelift"] if self._theme == "facelift" else [self._theme, "facelift"]

    @request_memoize()
    def detect_icon_path(self, icon_name: str, prefix: str) -> str:
        """Detect from which place an icon shall be used and return its path relative to htdocs/

        Priority:
        1. In case the modern-dark theme is active: <theme> = modern-dark -> priorities 3-6
        2. In case the facelift theme is active: <theme> = facelift -> priorities 3-6
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

        if icon_name == "missing" and prefix == "icon_":
            raise RuntimeError("Icon 'missing' not found in any icon path.")

        return self.detect_icon_path("missing", "icon_")

    def _find_icon_in_dir(self, icon_dir: str, icon_name: str, prefix: str) -> str | None:
        for base_dir in [str(cmk.utils.paths.local_web_dir), cmk.utils.paths.web_dir]:
            for file_type in ["svg", "png"]:
                rel_path = icon_dir + "/" + prefix + icon_name + "." + file_type
                if os.path.exists(base_dir + "/htdocs/" + rel_path):
                    return rel_path

        return None

    def url(self, rel_url: str) -> str:
        return f"themes/{self._theme}/{rel_url}"

    def base_dir(self) -> Path:
        return cmk.utils.paths.local_web_dir / "htdocs" / "themes" / self._theme

    def has_custom_logo(self, logo_name: str) -> bool:
        """Whether or not the current CME customer has a custom logo

        CME snapshot sync copies the customer logo to themes/facelift/images/<logo_name>.png.
        See CMESnapshotDataCollector._update_customer_sidebar_top.
        """
        return (
            edition(cmk.utils.paths.omd_root) is Edition.CME
            and self.base_dir().joinpath("images", f"{logo_name}.png").exists()
        )


def theme_choices() -> list[tuple[str, str]]:
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


theme = request_local_attr("theme", Theme)
