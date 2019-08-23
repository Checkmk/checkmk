#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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
"""Tool for updating Checkmk configuration files after version updates

This command is normally executed automatically at the end of "omd update" on
all sites and on remote sites after receiving a snapshot and does not need to
be called manually.",
"""

from __future__ import (
    absolute_import,
    division,
    print_function,
)

try:
    from pathlib import Path  # type: ignore # pylint: disable=unused-import
except ImportError:
    from pathlib2 import Path  # pylint: disable=unused-import

from typing import List  # pylint: disable=unused-import
import argparse
import logging  # pylint: disable=unused-import
from werkzeug.test import create_environ

import cmk_base.autochecks

import cmk.utils.log
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils
import cmk.gui.watolib.tags
import cmk.gui.watolib.hosts_and_folders
import cmk.gui.watolib.rulesets
import cmk.gui.modules
import cmk.gui.config
import cmk.gui.htmllib as htmllib
from cmk.gui.globals import html, current_app
from cmk.gui.http import Request, Response


# TODO: Better make our application available?
class DummyApplication(object):
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response
        self.g = {}


class UpdateConfig(object):
    def __init__(self, logger, arguments):
        # type: (logging.Logger, argparse.Namespace) -> None
        super(UpdateConfig, self).__init__()
        self._arguments = arguments
        self._logger = logger

    def run(self):
        self._logger.info("Updating Checkmk configuration with \"cmk-update-config -v\"")
        self._initialize_gui_environment()

        for step_func, title in self._steps():
            self._logger.info(" + %s..." % title)
            step_func()

        self._logger.info("Done")

    def _steps(self):
        return [
            (self._rewrite_wato_tag_config, "Rewriting WATO tags"),
            (self._rewrite_wato_host_and_folder_config, "Rewriting WATO hosts and folders"),
            (self._rewrite_wato_rulesets, "Rewriting WATO rulesets"),
            (self._rewrite_autochecks, "Rewriting autochecks"),
        ]

    def _rewrite_wato_tag_config(self):
        tag_config_file = cmk.gui.watolib.tags.TagConfigFile()
        tag_config = cmk.utils.tags.TagConfig()
        tag_config.parse_config(tag_config_file.load_for_reading())
        tag_config_file.save(tag_config.get_dict_format())

    def _rewrite_wato_host_and_folder_config(self):
        root_folder = cmk.gui.watolib.hosts_and_folders.Folder.root_folder()
        root_folder.save()
        root_folder.rewrite_hosts_files()

    def _rewrite_autochecks(self):
        for autocheck_file in Path(cmk.utils.paths.autochecks_dir).glob("*.mk"):
            hostname = autocheck_file.stem
            autochecks = cmk_base.autochecks.parse_autochecks_file(hostname)
            cmk_base.autochecks.save_autochecks_file(hostname, autochecks)

    def _rewrite_wato_rulesets(self):
        all_rulesets = cmk.gui.watolib.rulesets.AllRulesets()
        all_rulesets.load()
        all_rulesets.save()

    def _initialize_gui_environment(self):
        environ = dict(create_environ(), REQUEST_URI='')
        current_app.set_current(DummyApplication(environ, None))
        html.set_current(htmllib.html(Request(environ), Response(is_secure=False)))

        cmk.gui.modules.load_all_plugins()
        # TODO: We are about to rewrite parts of the config. Would be better to be executable without
        # loading the configuration first (because the load_config() may miss some conversion logic
        # which is only known to cmk.update_config in the future).
        cmk.gui.config.load_config()
        cmk.gui.config.set_super_user()


def main(args):
    # type: (List[str]) -> int
    arguments = parse_arguments(args)

    try:
        cmk.utils.log.setup_console_logging()
        cmk.utils.log.set_verbosity(arguments.verbose)
        if arguments.debug:
            cmk.utils.debug.enable()
        logger = cmk.utils.log.get_logger("update_config")

        logger.debug("parsed arguments: %s", arguments)

        UpdateConfig(logger, arguments).run()

    except Exception as e:
        if arguments.debug:
            raise
        if logger:
            logger.exception("ERROR: Please repair this and run \"cmk-update-config -v\"")
        else:
            print("ERROR: %s" % e)
        return 1
    return 0


def parse_arguments(args):
    # type: (List[str]) -> argparse.Namespace
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--debug', action='store_true', help='Debug mode: raise Python exceptions')
    p.add_argument('-v',
                   '--verbose',
                   action='count',
                   default=0,
                   help='Verbose mode (use multiple times for more output)')

    arguments = p.parse_args(args)
    return arguments
