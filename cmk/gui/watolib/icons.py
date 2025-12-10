#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from cmk.gui.i18n import _
from cmk.gui.theme import Theme
from cmk.utils import paths
from cmk.utils.images import CMKImage, ImageType

_DEFAULT_BUILT_IN_CATEGORY: Final = "builtin"
_DEFAULT_USER_CATEGORY: Final = "misc"


@dataclass(slots=True, kw_only=True, frozen=True)
class IconData:
    id: str
    path: str  # relative path, usable in frontend
    category_id: str
    is_built_in: bool


def all_icon_categories(wato_icon_categories: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    """Returns all icon categories, including the default ones."""
    categories = list(wato_icon_categories)
    # ensure the default categories for user defined and built in icons exist
    ids = {k for k, _v in categories}
    if _DEFAULT_USER_CATEGORY not in ids:
        categories.append((_DEFAULT_USER_CATEGORY, _("Misc")))
    if _DEFAULT_BUILT_IN_CATEGORY not in ids:
        categories.append((_DEFAULT_BUILT_IN_CATEGORY, _("Built-in")))
    return categories


def all_available_icons(
    theme: Theme, *, wato_icon_categories: Iterable[tuple[str, str]], only_local: bool = False
) -> Mapping[str, str]:
    """Returns a mapping of icon id to category id for all available icons.

    This includes built-in icons as well as user-defined icons. The user defined ones can override
    built-in ones."""
    return {
        icon.id: icon.category_id
        for icon in all_available_icon_data(
            theme, wato_icon_categories=wato_icon_categories, only_local=only_local
        )
    }


def all_available_icon_data(
    theme: Theme, *, wato_icon_categories: Iterable[tuple[str, str]], only_local: bool = False
) -> Iterable[IconData]:
    """Returns all available icons.

    This includes built-in icons as well as user-defined icons. The user defined ones can override
    built-in ones."""
    icons = {
        icon.id: icon
        for icon in _available_built_in_icon_data(
            theme, wato_icon_categories=wato_icon_categories, only_local=only_local
        )
    }
    icons.update(
        {
            icon.id: icon
            for icon in _available_user_icon_data(
                wato_icon_categories=wato_icon_categories, only_local=only_local
            )
        }
    )
    return icons.values()


def all_available_icon_emblems(
    theme: Theme, *, wato_icon_categories: Iterable[tuple[str, str]], only_local: bool = False
) -> Mapping[str, str]:
    """Returns a mapping of icon emblem id to category id for all available icon emblems."""
    return {
        emblem.id: emblem.category_id
        for emblem in all_available_icon_emblem_data(
            theme, wato_icon_categories=wato_icon_categories, only_local=only_local
        )
    }


def all_available_icon_emblem_data(
    theme: Theme, *, wato_icon_categories: Iterable[tuple[str, str]], only_local: bool = False
) -> Iterable[IconData]:
    """Returns all available icon emblems."""
    # no user defined emblems for now
    return _available_built_in_icon_emblem_data(
        theme, wato_icon_categories=wato_icon_categories, only_local=only_local
    )


def _available_built_in_icon_data(
    theme: Theme, *, wato_icon_categories: Iterable[tuple[str, str]], only_local: bool = False
) -> Iterable[IconData]:
    """Returns all available built-in icons."""
    return _available_built_in_icon_data_by_prefix(
        theme, prefix="icon_", wato_icon_categories=wato_icon_categories, only_local=only_local
    )


def _available_built_in_icon_emblem_data(
    theme: Theme, *, wato_icon_categories: Iterable[tuple[str, str]], only_local: bool = False
) -> Iterable[IconData]:
    """Returns all available built-in icon emblems."""
    return _available_built_in_icon_data_by_prefix(
        theme, prefix="emblem_", wato_icon_categories=wato_icon_categories, only_local=only_local
    )


def _available_built_in_icon_data_by_prefix(
    theme: Theme,
    prefix: str,
    *,
    wato_icon_categories: Iterable[tuple[str, str]],
    only_local: bool = False,
) -> Iterable[IconData]:
    """Returns all available built-in icons with the given prefix.

    The prefix is used to distinguish between normal icons and icon emblems.
    The returned IconData objects will have the prefix stripped from their id.
    """
    base_dirs: list[Path] = [paths.local_web_dir]
    if not only_local:
        base_dirs.append(paths.web_dir)

    icons: dict[str, IconData] = {}
    valid_categories = {k for k, _v in all_icon_categories(wato_icon_categories)}
    for theme_id in theme.icon_themes():
        for base_dir in base_dirs:
            directory = base_dir / "htdocs/themes" / theme_id / "images"

            for file, category in _get_icons_from_directory(
                directory,
                valid_categories,
                default_category=_DEFAULT_BUILT_IN_CATEGORY,
                file_prefix=prefix,
            ).items():
                icon_id = file.stem[len(prefix) :]
                if icon_id in icons:
                    # prefer first found icon, active theme > local directory > rest
                    continue

                icons[icon_id] = IconData(
                    id=icon_id,
                    path=str(file.relative_to(base_dir / "htdocs")),
                    category_id=category,
                    is_built_in=True,
                )

    return icons.values()


def _available_user_icon_data(
    *, wato_icon_categories: Iterable[tuple[str, str]], only_local: bool = False
) -> Iterable[IconData]:
    """Returns all available user-defined icons."""
    base_dirs: list[Path] = [paths.local_web_dir]
    if not only_local:
        base_dirs.append(paths.web_dir)

    icons: dict[str, IconData] = {}
    valid_categories = {k for k, _v in all_icon_categories(wato_icon_categories)}
    for base_dir in base_dirs:
        directory = base_dir / "htdocs/images/icons"
        for file, category in _get_icons_from_directory(
            directory, valid_categories, default_category=_DEFAULT_USER_CATEGORY
        ).items():
            icon_id = file.stem
            if icon_id in icons:
                continue  # prefer first found icon, as that will be from the local directory

            icons[icon_id] = IconData(
                id=icon_id,
                path=str(file.relative_to(base_dir / "htdocs")),
                category_id=category,
                is_built_in=False,
            )

    return icons.values()


def _get_icons_from_directory(
    directory: Path,
    valid_categories: set[str],
    default_category: str,
    file_prefix: str | None = None,
) -> Mapping[Path, str]:
    """Scans the given directory for icons and extracts their categories."""
    icons: dict[Path, str] = {}
    try:
        files = [f for f in directory.iterdir() if f.is_file()]
    except OSError:
        return icons

    for file in files:
        if file_prefix and not file.stem.startswith(file_prefix):
            continue

        if file.suffix == ".png":
            try:
                category = _extract_category_from_png(file, valid_categories, default_category)
            except OSError as e:
                if "%s" % e == "cannot identify image file":
                    continue  # silently skip invalid files
                raise
        elif file.suffix == ".svg":
            # users are not able to add SVGs and our builtin SVGs don't have a category
            category = default_category
        else:
            continue

        icons[file] = category

    return icons


# All icons within the images/icons directory have the ident of a category
# witten in the PNG metadata. For the default images we have done this scripted.
# During upload of user specific icons, the metadata is added to the images.
def _extract_category_from_png(file_path: Path, valid_categories: set[str], default: str) -> str:
    image = CMKImage.from_path(file_path, ImageType.PNG)
    category = image.get_comment()
    if category not in valid_categories:
        return default
    return category
