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

import __builtin__
import os
import gettext as gettext_module
from typing import NamedTuple, Optional, List, Tuple

import cmk.paths

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

Translation = NamedTuple("Translation", [
    ("translation", gettext_module.NullTranslations),
    ("name", str)
])

# Current active translation object
_translation = None # type: Optional[Translation]

def _(message):
    # type: (str) -> unicode
    if not _translation:
        return unicode(message)
    else:
        return _translation.translation.ugettext(message)


def get_current_language():
    # type: () -> Optional[str]
    if _translation:
        return _translation.name
    else:
        return None


def _get_language_dirs():
    # type: () -> List[str]
    return [ cmk.paths.locale_dir, cmk.paths.local_locale_dir ]


def get_language_alias(lang):
    # type: (str) -> unicode
    alias = lang
    for lang_dir in _get_language_dirs():
        try:
            alias = open('%s/%s/alias' % (lang_dir, lang), 'r').read().strip()
        except (OSError, IOError):
            pass
    return alias


def get_languages():
    # type: () -> List[Tuple[str, unicode]]
    # Add the hard coded english language to the language list
    # It must be choosable even if the administrator changed the default
    # language to a custom value
    languages = set([ ('', _('English')) ])

    for lang_dir in _get_language_dirs():
        try:
            languages.update([ (val, _("%s") % get_language_alias(val))
                for val in os.listdir(lang_dir) if not '.' in val ])
        except OSError:
            # Catch "OSError: [Errno 2] No such file or
            # directory:" when directory not exists
            pass

    return list(languages)


def unlocalize():
    # type: () -> None
    global _translation
    _translation = None


def localize(lang):
    # type: (str) -> None
    set_language_cookie(lang)
    _do_localize(lang)


def _do_localize(lang):
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
    try:
        translation = gettext_module.translation("multisite", _get_cmk_locale_path(lang),
                languages = [ lang ], codeset = 'UTF-8') # type: Optional[gettext_module.NullTranslations]
    except IOError, e:
        translation = None

    return translation


def _get_cmk_locale_path(lang):
    # type: (str) -> str
    po_path = '/%s/LC_MESSAGES/multisite.mo' % lang
    if os.path.exists(cmk.paths.local_locale_dir + po_path):
        return cmk.paths.local_locale_dir
    else:
        return cmk.paths.locale_dir


def initialize():
    # type: () -> None
    unlocalize()


def del_language_cookie():
    html.response.del_cookie("language")


def set_language_cookie(lang):
    cookie_lang = html.request.cookie("language")
    if cookie_lang != lang:
        if lang != None:
            html.response.set_cookie("language", lang)
        else:
            del_language_cookie()


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


# Localization of user supplied texts
def _u(text):
    # type: (unicode) -> unicode
    # TODO: Reimplement this once config is available in "cmk.gui"!
    #import config
    #ldict = config.user_localizations.get(text)
    #if ldict:
    #    return ldict.get(get_current_language(), text)
    #else:
    return text


initialize()
