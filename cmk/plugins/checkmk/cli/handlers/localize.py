#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import cmk.utils.paths
from cmk.ccc import tty
from cmk.ccc.exceptions import MKException
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.checkmk.cli.localize import (
    cli_command_localize,
)
from cmk.utils.log import VERBOSE

_logger = logging.getLogger("cmk.base.localize")


_LanguageName = str


class _LocalizeException(MKException):
    pass


_domain = "multisite"


def _locale_base() -> Path:
    return cmk.utils.paths.local_locale_dir


def _pot_file() -> Path:
    if (local_pot_file := cmk.utils.paths.local_locale_dir / "multisite.pot").exists():
        return local_pot_file
    return _locale_base() / "multisite.pot"


def _builtin_po_file(lang: str) -> Path:
    return cmk.utils.paths.locale_dir / lang / "LC_MESSAGES" / ("%s.po" % _domain)


def _po_file(lang: str) -> Path:
    return _locale_base() / lang / f"LC_MESSAGES/{_domain}.po"


def _mo_file(lang: str) -> Path:
    return _locale_base() / lang / f"LC_MESSAGES/{_domain}.mo"


def _alias_file(lang: str) -> Path:
    return Path(_locale_base(), lang, "alias")


def _write_usage_to_stderr() -> None:
    sys.stderr.write(
        """Usage: check_mk [-v] --localize COMMAND [ARGS]

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
"""
        % _locale_base()
    )


def _do_localize(args: Sequence[str]) -> CLIExitCode:
    if len(args) == 0:
        _write_usage_to_stderr()
        return CLIExitCode.FAILURE

    command = args[0]

    try:
        lang: _LanguageName = args[1]
    except IndexError:
        raise _LocalizeException("No language given")

    if not lang:
        raise _LocalizeException("No language given")

    alias: str | None = None
    if len(args) > 2:
        alias = args[2]

    commands = {
        "update": _localize_update,
        "compile": _localize_compile,
        "edit": _localize_edit,
    }
    f = commands.get(command)
    if f:
        _check_binaries()

        try:
            f(lang)
            _write_alias(lang, alias)
        except _LocalizeException as e:
            # Expected CLI error, the traceback adds no value here.
            _logger.error("%(error)s", {"error": e})  # noqa: TRY400
            return CLIExitCode.FAILURE
    else:
        allc = sorted(commands.keys())
        allc = [tty.bold + c + tty.normal for c in allc]
        _logger.error(
            "Invalid localize command. Allowed are: %(commands)s and %(last_command)s.",
            {"commands": ", ".join(allc[:-1]), "last_command": allc[-1]},
        )
        return CLIExitCode.FAILURE
    return CLIExitCode.SUCCESS


def _write_alias(lang: _LanguageName, alias: str | None) -> None:
    if not alias:
        return

    alias_file_path = _alias_file(lang)
    if alias == "-" and alias_file_path.exists():
        alias_file_path.unlink()
        return

    with alias_file_path.open("w", encoding="utf-8") as f:
        f.write(alias)


def _check_binaries() -> None:
    """Are the xgettext utils available?"""
    for b in ["xgettext", "msgmerge", "msgfmt"]:
        if (
            subprocess.call(
                ["which", b],
                stdout=subprocess.DEVNULL,
            )
            != 0
        ):
            raise _LocalizeException("%s binary not found in PATH\n" % b)


def _get_languages() -> list[_LanguageName]:
    return [l.name for l in _locale_base().iterdir() if l.is_dir()]


def _localize_update_po(lang: _LanguageName) -> None:
    """Merge the current .pot file with a given .po file"""
    _logger.log(VERBOSE, "Merging translations...")
    if (
        subprocess.call(
            ["msgmerge", "-U", _po_file(lang), _pot_file()],
            stdout=subprocess.DEVNULL,
        )
        != 0
    ):
        _logger.error("Failed!")
    else:
        _logger.info("Success! Output: %(output)s", {"output": _po_file(lang)})


def _localize_init_po(lang: _LanguageName) -> None:
    if (
        subprocess.call(
            ["msginit", "-i", _pot_file(), "--no-translator", "-l", lang, "-o", _po_file(lang)],
            stdout=subprocess.DEVNULL,
        )
        != 0
    ):
        _logger.error("Failed!\n")


def _localize_sniff() -> None:
    """Dig into the source code and generate a new .pot file"""
    _logger.info("Sniffing source code...")

    paths = [
        str(cmk.utils.paths.default_config_dir),
        str(cmk.utils.paths.web_dir / "app"),
        str(cmk.utils.paths.lib_dir / "python/cmk"),
    ]
    if cmk.utils.paths.local_web_dir.exists():
        paths.append(str(cmk.utils.paths.local_web_dir))

    sniff_files = []
    for path in paths:
        for root, _dirs, files in os.walk(path):
            for f in files:
                if f.endswith((".py", ".mk")):
                    sniff_files.append(os.path.join(root, f))

    if (
        subprocess.call(
            [
                "xgettext",
                "--no-wrap",
                "--sort-output",
                "--force-po",
                "-L",
                "Python",
                "--from-code=utf-8",
                "--omit-header",
                "-o",
                _pot_file(),
                *sniff_files,
            ],
            stdout=subprocess.DEVNULL,
        )
        != 0
    ):
        _logger.error("Failed!\n")
    else:
        header = r"""# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
msgid ""
msgstr ""
"Project-Id-Version: Checkmk user interface translation 0.1\n"
"Report-Msgid-Bugs-To: checkmk-en@lists.mathias-kettner.de\n"
"POT-Creation-Date: 2011-05-13 09:42+0200\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"Language: LANGUAGE \n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"

"""

        _pot_file().write_text(header + _pot_file().read_text())
        _logger.info("Success! Output: %(output)s", {"output": _pot_file()})


def _localize_edit(lang: _LanguageName) -> None:
    _localize_update(lang)

    editor = os.getenv("VISUAL", os.getenv("EDITOR", "/usr/bin/vi"))
    if not os.path.exists(editor):
        editor = "vi"

    if subprocess.call([editor, _po_file(lang)]) == 0:
        _localize_compile(lang)
    else:
        _logger.error("Aborted.")


def _localize_update(lang: _LanguageName) -> None:
    """Start translating in a new language"""
    _initialize_local_po_file(lang)
    _localize_sniff()

    if not _po_file(lang).exists():
        _logger.info("Initializing .po file for language %(lang)s...", {"lang": lang})
        _localize_init_po(lang)
    else:
        _logger.info("Updating .po file for language %(lang)s...", {"lang": lang})
        _localize_update_po(lang)


def _localize_compile(lang: _LanguageName) -> None:
    """Create a .mo file from the given .po file"""
    if lang not in _get_languages():
        raise _LocalizeException(
            "Invalid language given. Available: %s" % " ".join(_get_languages())
        )

    po_file = _po_file(lang)
    _initialize_local_po_file(lang)

    if not po_file.exists():
        raise _LocalizeException("The .po file %s does not exist." % po_file)

    if subprocess.call(["msgfmt", po_file, "-o", _mo_file(lang)]) != 0:
        _logger.error("Failed!")
    else:
        _logger.info("Success! Output: %(output)s", {"output": _mo_file(lang)})


def _initialize_local_po_file(lang: _LanguageName) -> None:
    """Initialize the file in the local hierarchy with the file in the default hierarchy if needed"""
    po_file = _po_file(lang)
    po_file.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
    builtin_po_file = _builtin_po_file(lang)
    if not po_file.exists() and builtin_po_file.exists():
        po_file.write_text(
            builtin_po_file.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        _logger.info(
            "Initialize %(po_file)s with the file in the default hierarchy", {"po_file": po_file}
        )


def _run_localize(_context: CLIContext, arguments: Sequence[str]) -> CLIExitCode:
    return _do_localize(arguments)


cli_handler_localize = CLIHandler(command=cli_command_localize, run=_run_localize)
