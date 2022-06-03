#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
# Library for pylint checks of Checkmk

import glob
import multiprocessing
import os
import subprocess
import time
from pathlib import Path

from pylint.message.message import Message  # type: ignore[import]
from pylint.reporters.text import (  # type: ignore[import]
    ColorizedTextReporter,
    ParseableTextReporter,
)

from tests.testlib import cmk_path, is_enterprise_repo, repo_path


def check_files(base_dir):
    filelist = sorted([base_dir + "/" + f for f in os.listdir(base_dir) if not f.startswith(".")])

    # Sort: first includes, then other
    filelist = [f for f in filelist if f.endswith(".include")] + [
        f for f in filelist if not f.endswith(".include")
    ]

    return filelist


def add_file(f, path):
    relpath = os.path.relpath(os.path.realpath(path), cmk_path())
    f.write("# -*- encoding: utf-8 -*-")
    f.write("#\n")
    f.write("# ORIG-FILE: " + relpath + "\n")
    f.write("#\n")
    f.write("\n")
    f.write(Path(path).read_text())


def run_pylint(base_path, check_files):
    args = os.environ.get("PYLINT_ARGS", "")
    if args:
        pylint_args = args.split(" ")
    else:
        pylint_args = []

    pylint_cfg = repo_path() + "/.pylintrc"

    cmd = [
        "python",
        "-m",
        "pylint",
        "--rcfile",
        pylint_cfg,
        "--jobs=%d" % num_jobs_to_use(),
    ]
    files = pylint_args + check_files

    print(
        f"Running pylint in '{base_path}' with: {subprocess.list2cmdline(cmd)}"
        f" [{len(files)} files omitted]"
    )
    exit_code = subprocess.run(cmd + files, shell=False, cwd=base_path, check=False).returncode
    print(f"Finished with exit code: {exit_code}")

    return exit_code


def num_jobs_to_use():
    # Naive heuristic, but looks OK for our use cases:\ Normal quad core CPUs
    # with HT report 8 CPUs (=> 6 jobs), our server 24-core CPU reports 48 CPUs
    # (=> 11 jobs). Just using 0 (meaning: use all reported CPUs) might just
    # work, too, but it's probably a bit too much.
    #
    # On our CI server there are currently up to 5 parallel Gerrit jobs allowed
    # which trigger pylint + 1 explicit pylint job per Checkmk branch. This
    # means that there may be up to 8 pylint running in parallel. Currently
    # these processes consume about 400 MB of rss memory.  To prevent swapping
    # we need to reduce the parallelization of pylint for the moment.
    if os.environ.get("USER") == "jenkins":
        return int(multiprocessing.cpu_count() / 8.0) + 3
    return int(multiprocessing.cpu_count() / 8.0) + 5


def get_pylint_files(base_path, file_pattern):
    files = []
    for path in glob.glob("%s/%s" % (base_path, file_pattern)):
        f = path[len(base_path) + 1 :]

        if f.endswith(".pyc"):
            continue

        if is_python_file(path):
            files.append(f)

    return files


def is_python_file(path, shebang_name=None):
    if shebang_name is None:
        shebang_name = "python3"

    if not os.path.isfile(path) or os.path.islink(path):
        return False

    # Only add python files
    with open(path, "r") as f:
        shebang = f.readline().rstrip()
    if shebang.startswith("#!") and shebang.endswith(shebang_name):
        return True

    return False


# Checkmk currently uses a packed version of it's files to
# run the pylint tests because it's not well structured in
# python modules. This custom reporter rewrites the found
# messages to tell the users the original location in the
# python sources
# TODO: This can be dropped once we have refactored checks/inventory/bakery plugins
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

    def _change_path_to_repo_path(self, msg):
        return os.path.relpath(msg.abspath, cmk_path())

    def _orig_location_from_compiled_file(self, msg):
        with open(msg.abspath) as fmsg:
            lines = fmsg.readlines()
        line_nr = msg.line
        orig_file, went_back = None, -3
        while line_nr > 0:
            line_nr -= 1
            went_back += 1
            line = lines[line_nr]
            if line.startswith("# ORIG-FILE: "):
                orig_file = line.split(": ", 1)[1].strip()
                break
        return orig_file, (None if orig_file is None else went_back)


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
def register(linter):
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
