#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import gettext as gettext_module
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

import cmk.utils.paths

from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.utils.speaklater import LazyString

# .
#   .--Gettext i18n--------------------------------------------------------.
#   |           ____      _   _            _     _ _  ___                  |
#   |          / ___| ___| |_| |_ _____  _| |_  (_) |( _ ) _ __            |
#   |         | |  _ / _ \ __| __/ _ \ \/ / __| | | |/ _ \| '_ \           |
#   |         | |_| |  __/ |_| ||  __/>  <| |_  | | | (_) | | | |          |
#   |          \____|\___|\__|\__\___/_/\_\\__| |_|_|\___/|_| |_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Handling of the regular localization of the GUI                      |
#   '----------------------------------------------------------------------'


# NullTranslations is the base class used by all translation classes in gettext
class Translation(NamedTuple):
    translation: gettext_module.NullTranslations
    name: str


def _translation() -> Optional[Translation]:
    try:
        return request_local_attr().translation
    except RuntimeError:
        # TODO: Once we cleaned up all wrong _() to _l(), we can clean this up
        pass
    return None


def _(message: str, /) -> str:
    """
    Positional-only argument to simplify additional linting of localized strings.
    """
    if translation := _translation():
        return translation.translation.gettext(message)
    return str(message)


def _l(string: str, /) -> LazyString:
    """Like _() but the string returned is lazy which means it will be translated when it is used as
    an actual string. Positional-only arguments to simplify additional linting of localized
    strings."""
    return LazyString(_, string)


def ungettext(singular: str, plural: str, n: int, /) -> str:
    """
    Positional-only argument to simplify additional linting of localized strings
    """
    if translation := _translation():
        return translation.translation.ngettext(singular, plural, n)
    if n == 1:
        return str(singular)
    return str(plural)


def get_current_language() -> Optional[str]:
    if translation := _translation():
        return translation.name
    return None


def _get_language_dirs() -> List[Path]:
    return _get_base_language_dirs() + _get_package_language_dirs()


def _get_base_language_dirs() -> List[Path]:
    return [cmk.utils.paths.locale_dir, cmk.utils.paths.local_locale_dir]


def _get_package_language_dirs() -> List[Path]:
    """Return a list of extension package specific localization directories

    It's possible for extension packages to provide custom localization files
    which are meant for localizing extension specific texts. These localizations
    are then used in addition to the builtin and local localization files.
    """
    package_locale_dir = cmk.utils.paths.local_locale_dir / "packages"
    if not package_locale_dir.exists():
        return []
    return list(package_locale_dir.iterdir())


def get_language_alias(lang: Optional[str]) -> str:
    if lang is None:
        return _("English")

    alias = lang
    for lang_dir in _get_base_language_dirs():
        try:
            with (lang_dir / lang / "alias").open(encoding="utf-8") as f:
                alias = f.read().strip()
        except (OSError, IOError):
            pass
    return alias


def get_languages() -> List[Tuple[str, str]]:
    # Add the hard coded english language to the language list
    # It must be choosable even if the administrator changed the default
    # language to a custom value
    languages = {("", _("English"))}

    for lang_dir in _get_language_dirs():
        try:
            languages.update(
                [
                    (val.name, _("%s") % get_language_alias(val.name))
                    for val in lang_dir.iterdir()
                    if val.name != "packages" and val.is_dir()
                ]
            )
        except OSError:
            # Catch "OSError: [Errno 2] No such file or
            # directory:" when directory not exists
            pass

    return sorted(list(languages), key=lambda x: x[1])


def unlocalize() -> None:
    request_local_attr().translation = None


def localize(lang: Optional[str]) -> None:
    if lang is None:
        unlocalize()
        return

    gettext_translation = _init_language(lang)
    if not gettext_translation:
        unlocalize()
        return

    request_local_attr().translation = Translation(translation=gettext_translation, name=lang)


def _init_language(lang: str) -> Optional[gettext_module.NullTranslations]:
    """Load all available "multisite" translation files. All are loaded first.
    The builtin ones are used as "fallback" for the local files which means that
    the texts in the local files have precedence.
    """
    translations: List[gettext_module.NullTranslations] = []
    for locale_base_dir in _get_language_dirs():
        try:
            translation = gettext_module.translation(
                "multisite", str(locale_base_dir), languages=[lang]
            )

        except IOError:
            continue

        # Create a chain of fallback translations
        if translations:
            translation.add_fallback(translations[-1])
        translations.append(translation)

    if not translations:
        return None

    return translations[-1]


# .
#   .--User i18n-----------------------------------------------------------.
#   |                _   _                 _ _  ___                        |
#   |               | | | |___  ___ _ __  (_) |( _ ) _ __                  |
#   |               | | | / __|/ _ \ '__| | | |/ _ \| '_ \                 |
#   |               | |_| \__ \  __/ |    | | | (_) | | | |                |
#   |                \___/|___/\___|_|    |_|_|\___/|_| |_|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Users can localize custom strings using the global configuration     |
#   '----------------------------------------------------------------------'

_user_localizations: Dict[str, Dict[str, str]] = {}


# Localization of user supplied texts
def _u(text: str) -> str:
    ldict = _user_localizations.get(text)
    if ldict:
        current_language = get_current_language()
        if current_language is None:
            return text
        return ldict.get(current_language, text)
    if translation := _translation():
        return translation.translation.gettext(text)
    return text


def set_user_localizations(localizations: Dict[str, Dict[str, str]]) -> None:
    _user_localizations.clear()
    _user_localizations.update(localizations)
