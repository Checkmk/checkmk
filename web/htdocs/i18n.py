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

import __builtin__, os, gettext
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
#   | Handling of the regular localizatoon of the GUI                      |
#   '----------------------------------------------------------------------'

# Language specific translation objects. One object for each translation,
# indexed by the internal language id
translations = {}

def get_current_language():
    return current_language

def get_language_dirs():
    return [ cmk.paths.locale_dir, cmk.paths.local_locale_dir ]


def get_language_alias(lang):
    alias = lang
    for lang_dir in get_language_dirs():
        try:
            alias = file('%s/%s/alias' % (lang_dir, lang), 'r').read().strip()
        except (OSError, IOError):
            pass
    return alias


def get_languages():
    # Add the hard coded english language to the language list
    # It must be choosable even if the administrator changed the default
    # language to a custom value
    languages = set([ ('', _('English')) ])

    for lang_dir in get_language_dirs():
        try:
            languages.update([ (val, _("%s") % get_language_alias(val))
                for val in os.listdir(lang_dir) if not '.' in val ])
        except OSError:
            # Catch "OSError: [Errno 2] No such file or
            # directory:" when directory not exists
            pass

    return list(languages)


def get_cmk_locale_path(lang):
    po_path = '/%s/LC_MESSAGES/multisite.mo' % lang
    if os.path.exists(cmk.paths.local_locale_dir + po_path):
        return cmk.paths.local_locale_dir
    else:
        return cmk.paths.locale_dir


def init_language(lang, domain="multisite", locale_path=None):
    if locale_path == None:
        locale_path = get_cmk_locale_path(lang)

    try:
        translation = gettext.translation(domain, locale_path,
                                          languages = [ lang ], codeset = 'UTF-8')
    except IOError, e:
        translation = None

    translations[lang] = translation
    return translation


# Prepares the builtin-scope for localization, registers the _() function and
# current_language variable. Is also used to disable localization
def unlocalize():
    # TODO: Make behaviour like gettext _(): Always return unicode strings
    __builtin__._ = lambda x: x
    __builtin__.current_language = None


def localize(lang, **kwargs):
    set_language_cookie(lang)
    do_localize(lang, **kwargs)


def do_localize(lang, **kwargs):
    if lang:
        # FIXME: Clean this up. Make the other code access the current language through a
        # function of this module.
        __builtin__.current_language = lang

        translation = translations.get(lang, init_language(lang, **kwargs))
        if translation:
            translation.install(unicode = True)
        else:
            unlocalize() # Fallback to non localized multisite
    else:
        unlocalize()


def initialize():
    __builtin__._u = _u
    unlocalize()


def del_language_cookie():
    html.del_cookie("language")


def set_language_cookie(lang):
    cookie_lang = html.cookie("language", None)
    if cookie_lang != lang:
        if lang != None:
            html.set_cookie("language", lang)
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
    import config
    ldict = config.user_localizations.get(text)
    if ldict:
        return ldict.get(current_language, text)
    else:
        return text


initialize()
