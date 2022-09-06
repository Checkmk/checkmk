#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Library for pylint checks of Checkmk

import os
import time
from pathlib import Path

from pylint.lint import PyLinter  # type: ignore[import]
from pylint.message.message import Message  # type: ignore[import]
from pylint.reporters.text import (  # type: ignore[import]
    ColorizedTextReporter,
    ParseableTextReporter,
)

from tests.testlib import cmk_path, is_enterprise_repo


def is_python_file(path: Path, shebang_name: str | None = None) -> bool:
    if shebang_name is None:
        shebang_name = "python3"
    if not os.path.isfile(path) or os.path.islink(path):
        return False
    with path.open() as f:
        shebang = f.readline().rstrip()
    return shebang.startswith("#!") and shebang.endswith(shebang_name)


# Checkmk currently uses a packed version of it's files to
# run the pylint tests because it's not well structured in
# python modules. This custom reporter rewrites the found
# messages to tell the users the original location in the
# python sources
# TODO: This can be dropped once we have refactored checks/bakery plugins
# to real modules
class CMKFixFileMixin:
    def handle_message(self, msg: Message) -> None:
        if msg.abspath is None:
            # NOTE: I'm too lazy to define a Protocol for this mixin which is
            # already on death row, so let's use a reflection hack...
            getattr(super(), "handle_message")(msg)
            return

        new_path, new_line = self._orig_location_from_compiled_file(msg)

        if new_path is None:
            new_path = self._change_path_to_repo_path(msg)

        if new_path is not None:
            msg.path = new_path
        if new_line is not None:
            msg.line = new_line

        # NOTE: I'm too lazy to define a Protocol for this mixin which is
        # already on death row, so let's use a reflection hack...
        getattr(super(), "handle_message")(msg)

    def _change_path_to_repo_path(self, msg: Message) -> str:
        return os.path.relpath(msg.abspath, cmk_path())

    def _orig_location_from_compiled_file(
        self, msg: Message
    ) -> tuple[str, int] | tuple[None, None]:
        with open(msg.abspath) as fmsg:
            lines = fmsg.readlines()
        line_nr = msg.line
        went_back = -3
        while line_nr > 0:
            line_nr -= 1
            went_back += 1
            line = lines[line_nr]
            if line.startswith("# ORIG-FILE: "):
                return line.split(": ", 1)[1].strip(), went_back

        return None, None


class CMKOutputScanTimesMixin:
    """Prints out the files being checked and the time needed

    Can be useful to track down pylint performance issues. Simply make the
    reporter class inherit from this class to use it."""

    def on_set_current_module(self, modname, filepath):
        # HACK: See note above.
        getattr(super(), "on_set_current_module")(modname, filepath)
        if hasattr(self, "_current_start_time"):
            print(
                "% 8.3fs %s"
                % (
                    time.time() - getattr(self, "_current_start_time"),
                    getattr(self, "_current_filepath"),
                )
            )

        print("          %s..." % filepath)
        self._current_name = modname
        self._current_name = modname
        self._current_filepath = filepath
        self._current_start_time = time.time()

    def on_close(self, stats, previous_stats):
        # HACK: See note above.
        getattr(super(), "on_close")(stats, previous_stats)
        if hasattr(self, "_current_start_time"):
            print(
                "% 8.3fs %s"
                % (
                    time.time() - getattr(self, "_current_start_time"),
                    getattr(self, "_current_filepath"),
                )
            )


class CMKColorizedTextReporter(CMKFixFileMixin, ColorizedTextReporter):
    name = "cmk_colorized"


class CMKParseableTextReporter(CMKFixFileMixin, ParseableTextReporter):
    name = "cmk_parseable"


# Is called by pylint to load this plugin
def register(linter: PyLinter) -> None:
    # Disable some CEE/CME/CPE specific things when linting CRE repos
    if not is_enterprise_repo():
        # Is used to disable import-error. Would be nice if no-name-in-module could be
        # disabled using this, but this does not seem to be possible :(
        linter.global_set_option(
            "ignored-modules",
            "cmk.base.cee,cmk.gui.cee,cmk.gui.cme,cmk.gui.cme.managed,cmk.base.cpe,cmk.gui.cpe",
        )
        # This disables no-member errors
        linter.global_set_option(
            "generated-members",
            r"(cmk\.base\.cee|cmk\.gui\.cee|cmk\.gui\.cme|cmk\.base\.cpe|cmk\.gui\.cpe)(\..*)?",
        )

    linter.register_reporter(CMKColorizedTextReporter)
    linter.register_reporter(CMKParseableTextReporter)
