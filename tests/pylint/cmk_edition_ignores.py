#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pylint.lint import PyLinter

from tests.testlib.common.repo import is_pro_repo


# Is called by pylint to load this plugin
def register(linter: PyLinter) -> None:
    # Disable some CEE/CME/CCE specific things when linting CRE repos
    if not is_pro_repo():
        # Is used to disable import-error. Would be nice if no-name-in-module could be
        # disabled using this, but this does not seem to be possible :(
        linter.set_option(
            "ignored-modules",
            "cmk.base.nonfree.pro,cmk.gui.nonfree.pro,cmk.gui.nonfree.ultimatemt,cmk.gui.nonfree.ultimatemt.managed,cmk.gui.nonfree.ultimate,cmk.gui.nonfree.cloud",
        )
        # This disables no-member errors
        linter.set_option(
            "generated-members",
            r"(cmk\.base\.cee|cmk\.gui\.cee|cmk\.gui\.nonfree\.ultimatemt|cmk\.gui\.nonfree\.ultimate|cmk\.gui\.nonfree\.cloud)(\..*)?",
        )
