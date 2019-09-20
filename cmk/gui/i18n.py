#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import gettext as gettext_module
from typing import (  # pylint: disable=unused-import
    Dict, NamedTuple, Optional, List, Tuple, Text,
)
from pathlib2 import Path  # pylint: disable=unused-import

import cmk.utils.paths

#.
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
Translation = NamedTuple("Translation", [
    ("translation", gettext_module.NullTranslations),
    ("name", str),
])

# Current active translation object
_translation = None  # type: Optional[Translation]


def _(message):
    # type: (str) -> Text
    if not _translation:
        return unicode(message)
    return _translation.translation.ugettext(message)


def get_current_language():
    # type: () -> Optional[str]
    if _translation:
        return _translation.name
    return None


def _get_language_dirs():
    # type: () -> List[Path]
    return _get_base_language_dirs() + _get_package_language_dirs()


def _get_base_language_dirs():
    # type: () -> List[Path]
    return [Path(cmk.utils.paths.locale_dir), cmk.utils.paths.local_locale_dir]


def _get_package_language_dirs():
    # type: () -> List[Path]
    """Return a list of extension package specific localization directories

    It's possible for extension packages to provide custom localization files
    which are meant for localizing extension specific texts. These localizations
    are then used in addition to the builtin and local localization files.
    """
    package_locale_dir = cmk.utils.paths.local_locale_dir.joinpath("packages")
    if not package_locale_dir.exists():
        return []
    return list(package_locale_dir.iterdir())


def get_language_alias(lang):
    # type: (Optional[str]) -> Text
    if lang is None:
        return _("English")

    alias = lang
    for lang_dir in _get_base_language_dirs():
        try:
            with lang_dir.joinpath(lang, "alias").open(encoding="utf-8") as f:
                alias = f.read().strip()
        except (OSError, IOError):
            pass
    return alias


def get_languages():
    # type: () -> List[Tuple[str, Text]]
    # Add the hard coded english language to the language list
    # It must be choosable even if the administrator changed the default
    # language to a custom value
    languages = {('', _('English'))}

    for lang_dir in _get_language_dirs():
        try:
            languages.update([(val.name, _("%s") % get_language_alias(val.name))
                              for val in lang_dir.iterdir()
                              if val.name != "packages" and val.is_dir()])
        except OSError:
            # Catch "OSError: [Errno 2] No such file or
            # directory:" when directory not exists
            pass

    return sorted(list(languages), key=lambda x: x[1])


def unlocalize():
    # type: () -> None
    global _translation
    _translation = None


def localize(lang):
    # type: (str) -> None
    global _translation
    if lang is None:
        unlocalize()
        return

    gettext_translation = _init_language(lang)
    if not gettext_translation:
        unlocalize()
        return

    _translation = Translation(translation=gettext_translation, name=lang)


def _init_language(lang):
    # type: (str) -> Optional[gettext_module.NullTranslations]
    """Load all available "multisite" translation files. All are loaded first.
    The builtin ones are used as "fallback" for the local files which means that
    the texts in the local files have precedence.
    """
    translations = []  # type: List[gettext_module.NullTranslations]
    for locale_base_dir in _get_language_dirs():
        try:
            translation = gettext_module.translation("multisite",
                                                     str(locale_base_dir),
                                                     languages=[lang],
                                                     codeset='UTF-8')

        except IOError:
            continue

        # Create a chain of fallback translations
        if translations:
            translation.add_fallback(translations[-1])
        translations.append(translation)

    if not translations:
        return None

    return translations[-1]


def initialize():
    # type: () -> None
    unlocalize()


#.
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

_user_localizations = {}  # type: Dict[Text, Dict[Optional[str], Text]]


# Localization of user supplied texts
def _u(text):
    # type: (Text) -> Text
    ldict = _user_localizations.get(text)
    if ldict:
        return ldict.get(get_current_language(), text)
    return text


def set_user_localizations(localizations):
    # type: (Dict[Text, Dict[Optional[str], Text]]) -> None
    _user_localizations.clear()
    _user_localizations.update(localizations)


initialize()
