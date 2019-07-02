#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

import os
import subprocess
import sys

import cmk.utils.tty as tty
import cmk.utils.paths

import cmk.utils.log
logger = cmk.utils.log.get_logger(__name__)


# TODO: Inherit from MKGeneralException?
class LocalizeException(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(LocalizeException, self).__init__(reason)

    def __str__(self):
        return self.reason


domain = 'multisite'

pot_file = None
po_file = None
mo_file = None
alias_file = None
locale_base = cmk.utils.paths.local_locale_dir

if os.path.exists(cmk.utils.paths.local_locale_dir + '/multisite.pot'):
    pot_file = cmk.utils.paths.local_locale_dir + '/multisite.pot'
else:
    pot_file = locale_base + '/multisite.pot'

try:
    os.makedirs(locale_base)
except:
    pass


def localize_usage(err=''):
    sys.stdout.write("""Usage: check_mk [-v] --localize COMMAND [ARGS]

Available commands are:
  update  LANG [ALIAS] ... Creates or updates a .po file for the given
                           language. The alias is an optional attribute
                           which will be used as display string in the
                           Multisite GUI.
  compile LANG         ... Compiles the .po file into a .mo file which can
                           be used by gettext.
  edit    LANG         ... Call update, open .po in editor and compile in one step

 The regular process for translating is:

 1.) Create/update the .po file for the given language
 2.) Edit the .po file
 3.) Compile the .po file to get a .mo file which can be used by gettext

 Locale files are located in: %s
""" % locale_base)


def do_localize(args):
    if len(args) == 0:
        localize_usage()
        sys.exit(1)

    command = args[0]
    if len(args) > 1:
        lang = args[1]
    else:
        lang = None

    alias = None
    if len(args) > 2:
        alias = args[2]

    commands = {
        "update": localize_update,
        "compile": localize_compile,
        "edit": localize_edit,
    }
    f = commands.get(command)
    if f:
        check_binaries()

        try:
            f(lang)
            write_alias(alias)
        except LocalizeException as e:
            logger.error("%s" % e)
            sys.exit(1)
    else:
        allc = commands.keys()
        allc.sort()
        allc = [tty.bold + c + tty.normal for c in allc]
        logger.error("Invalid localize command. Allowed are: %s and %s.", ", ".join(allc[:-1]),
                     allc[-1])
        sys.exit(1)


def write_alias(alias):
    if not alias:
        return

    if alias == '-':
        os.remove(alias_file)
    else:
        file(alias_file, 'w').write(alias)


def check_binaries():
    # Are the xgettext utils available?
    for b in ['xgettext', 'msgmerge', 'msgfmt']:
        if subprocess.call(['which', b], stdout=open(os.devnull, "wb")) != 0:
            raise LocalizeException('%s binary not found in PATH\n' % b)


def get_languages():
    return [l for l in os.listdir(locale_base) if os.path.isdir(locale_base + '/' + l)]


def init_files(lang):
    global po_file, mo_file, alias_file
    po_file = locale_base + '/%s/LC_MESSAGES/%s.po' % (lang, domain)
    mo_file = locale_base + '/%s/LC_MESSAGES/%s.mo' % (lang, domain)
    alias_file = locale_base + '/%s/alias' % (lang)


def localize_update_po():
    # Merge the current .pot file with a given .po file
    logger.verbose("Merging translations...")
    if subprocess.call(['msgmerge', '-U', po_file, pot_file], stdout=open(os.devnull, "wb")) != 0:
        logger.error('Failed!')
    else:
        logger.info('Success! Output: %s', po_file)


def localize_init_po(lang):
    if subprocess.call(['msginit', '-i', pot_file, '--no-translator', '-l', lang, '-o', po_file],
                       stdout=open(os.devnull, "wb")) != 0:
        logger.error('Failed!\n')


# Dig into the source code and generate a new .pot file
def localize_sniff():
    logger.info('Sniffing source code...')

    paths = [
        cmk.utils.paths.default_config_dir,
        cmk.utils.paths.web_dir + "/app",
        cmk.utils.paths.lib_dir + "/python/cmk",
    ]
    if os.path.exists(cmk.utils.paths.local_web_dir):
        paths.append(cmk.utils.paths.local_web_dir)

    sniff_files = []
    for path in paths:
        for root, _dirs, files in os.walk(path):
            for f in files:
                if f.endswith(".py") or f.endswith(".mk"):
                    sniff_files.append(os.path.join(root, f))

    if subprocess.call(
        [
            'xgettext', '--no-wrap', '--sort-output', '--force-po', '-L', 'Python',
            '--from-code=utf-8', '--omit-header', '-o', pot_file
        ] + sniff_files,
            stdout=open(os.devnull, "wb")) != 0:
        logger.error('Failed!\n')
    else:
        header = r'''# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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
msgid ""
msgstr ""
"Project-Id-Version: Check_MK Multisite translation 0.1\n"
"Report-Msgid-Bugs-To: checkmk-en@lists.mathias-kettner.de\n"
"POT-Creation-Date: 2011-05-13 09:42+0200\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"Language: LANGUAGE \n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"

'''

        f = open(pot_file).read()
        open(pot_file, 'w').write(header + f)
        logger.info('Success! Output: %s', pot_file)


def localize_edit(lang):
    localize_update(lang)

    editor = os.getenv("VISUAL", os.getenv("EDITOR", "/usr/bin/vi"))
    if not os.path.exists(editor):
        editor = 'vi'

    if subprocess.call([editor, po_file]) == 0:
        localize_compile(lang)
    else:
        logger.error("Aborted.")


# Start translating in a new language
def localize_update(lang):
    if not lang:
        raise LocalizeException('No language given')

    init_files(lang)

    try:
        os.makedirs(os.path.dirname(po_file))
    except:
        pass

    # Maybe initialize the file in the local hierarchy with the file in
    # the default hierarchy
    if not os.path.exists(po_file) \
       and os.path.exists(cmk.utils.paths.locale_dir + '/%s/LC_MESSAGES/%s.po' % (lang, domain)):
        file(po_file, 'w').write(
            file(cmk.utils.paths.locale_dir + '/%s/LC_MESSAGES/%s.po' % (lang, domain)).read())
        logger.info('Initialize %s with the file in the default hierarchy', po_file)

    localize_sniff()

    if not os.path.exists(po_file):
        logger.info('Initializing .po file for language %s...', lang)
        localize_init_po(lang)
    else:
        logger.info('Updating .po file for language %s...', lang)
        localize_update_po()


# Create a .mo file from the given .po file
def localize_compile(lang):
    if not lang:
        raise LocalizeException('No language given')
    if lang not in get_languages():
        raise LocalizeException('Invalid language given. Available: %s' % ' '.join(get_languages()))

    init_files(lang)

    # Maybe initialize the file in the local hierarchy with the file in
    # the default hierarchy
    if not os.path.exists(po_file) \
       and os.path.exists(cmk.utils.paths.locale_dir + '/%s/LC_MESSAGES/%s.po' % (lang, domain)):
        file(po_file, 'w').write(
            file(cmk.utils.paths.locale_dir + '/%s/LC_MESSAGES/%s.po' % (lang, domain)).read())
        logger.info('Initialize %s with the file in the default hierarchy', po_file)

    if not os.path.exists(po_file):
        raise LocalizeException('The .po file %s does not exist.' % po_file)

    if subprocess.call(['msgfmt', po_file, '-o', mo_file]) != 0:
        logger.error('Failed!')
    else:
        logger.info('Success! Output: %s', mo_file)
