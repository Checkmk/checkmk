#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import gettext as gettext_module
from pathlib import Path
from typing import NamedTuple

import cmk.utils.paths

from cmk.gui.ctx_stack import global_var, request_local_attr, set_global_var
from cmk.gui.hooks import request_memoize
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


translation = request_local_attr("translation", Translation)


@request_memoize()
def translate_to_current_language(message: str) -> str:
    # Avoid localizing the empty string. The empty string is reserved for header data in PO files:
    # https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html
    # "An empty untranslated-string is reserved to contain the header entry with the meta
    # information". Hence, the localization of the empty string is the header data, which we
    # certainly do not want to display.
    if not message:
        return ""
    if translation:
        return translation.translation.gettext(message)
    return str(message)


def _(message: str, /) -> str:
    """
    Positional-only argument to simplify additional linting of localized strings.
    """
    return translate_to_current_language(message)


def _l(string: str, /) -> LazyString:
    """Like _() but the string returned is lazy which means it will be translated when it is used as
    an actual string. Positional-only arguments to simplify additional linting of localized
    strings."""
    return LazyString(_, string)


def ungettext(singular: str, plural: str, n: int, /) -> str:
    """
    Positional-only argument to simplify additional linting of localized strings
    """
    if translation:
        return translation.translation.ngettext(singular, plural, n)
    if n == 1:
        return str(singular)
    return str(plural)


def get_current_language() -> str:
    if translation:
        return translation.name
    return "en"


def _get_language_dirs() -> list[Path]:
    return _get_base_language_dirs() + _get_package_language_dirs()


def _get_base_language_dirs() -> list[Path]:
    return [cmk.utils.paths.locale_dir, cmk.utils.paths.local_locale_dir]


def _get_package_language_dirs() -> list[Path]:
    """Return a list of extension package specific localization directories

    It's possible for extension packages to provide custom localization files
    which are meant for localizing extension specific texts. These localizations
    are then used in addition to the built-in and local localization files.
    """
    package_locale_dir = cmk.utils.paths.local_locale_dir / "packages"
    if not package_locale_dir.exists():
        return []
    return list(package_locale_dir.iterdir())


def get_language_alias(lang: str) -> str:
    if lang == "en":
        return _("English")

    alias = lang
    for lang_dir in _get_base_language_dirs():
        try:
            with (lang_dir / lang / "alias").open(encoding="utf-8") as f:
                alias = f.read().strip()
        except OSError:
            pass
    return alias


def get_languages() -> list[tuple[str, str]]:
    # Add the hard coded english language to the language list
    # It must be choosable even if the administrator changed the default
    # language to a custom value
    languages = {("en", _("English"))}

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

    return sorted(list(languages), key=lambda x: (x[0] not in ["en", "de"], x[1]))


def _unlocalize() -> None:
    set_global_var("translation", None)


def localize(lang: str) -> None:
    translate_to_current_language.cache_clear()  # type: ignore[attr-defined]
    if lang == "en":
        _unlocalize()
        return None

    gettext_translation = _init_language(lang)
    if not gettext_translation:
        _unlocalize()
        return None

    set_global_var("translation", Translation(translation=gettext_translation, name=lang))
    return None


def _init_language(lang: str) -> gettext_module.NullTranslations | None:
    """Load all available "multisite" translation files. All are loaded first.
    The built-in ones are used as "fallback" for the local files which means that
    the texts in the local files have precedence.
    """
    translations: list[gettext_module.NullTranslations] = []
    for locale_base_dir in _get_language_dirs():
        try:
            set_global_var(
                "translation",
                gettext_module.translation("multisite", str(locale_base_dir), languages=[lang]),
            )

        except OSError:
            continue

        # Create a chain of fallback translations
        if translations:
            global_var("translation").add_fallback(translations[-1])
        translations.append(global_var("translation"))

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

_user_localizations: dict[str, dict[str, str]] = {}


# Localization of user supplied texts
def _u(text: str) -> str:
    ldict = _user_localizations.get(text)
    if ldict:
        current_language = get_current_language()
        if current_language == "en":
            return text
        return ldict.get(current_language, text)

    return translate_to_current_language(text)


def set_user_localizations(localizations: dict[str, dict[str, str]]) -> None:
    _user_localizations.clear()
    _user_localizations.update(localizations)
