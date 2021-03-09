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

import errno
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
import cmk.gui.utils
import cmk.gui.htmllib as htmllib
from cmk.gui.exceptions import MKIncompatiblePluginException
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
        self._logger.verbose("Initializing application...")
        self._initialize_gui_environment()

        self._logger.verbose("Updating Checkmk configuration...")
        for step_func, title in self._steps():
            self._logger.verbose(" + %s..." % title)
            step_func()

        self._logger.verbose("Done")

    def _steps(self):
        return [
            (self._rewrite_wato_tag_config, "Rewriting WATO tags"),
            (self._rewrite_wato_host_and_folder_config, "Rewriting WATO hosts and folders"),
            (self._rewrite_wato_rulesets, "Rewriting WATO rulesets"),
            (self._rewrite_autochecks, "Rewriting autochecks"),
            (self._cleanup_version_specific_caches, "Cleanup version specific caches"),
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

        # Currently the htmllib.html constructor enables the timeout by default. This side effect
        # should really be cleaned up.
        html.disable_request_timeout()

        self._logger.verbose("Loading GUI plugins...")
        cmk.gui.modules.load_all_plugins()
        failed_plugins = cmk.gui.utils.get_failed_plugins()

        if failed_plugins:
            _show_failed_plugin_error(self._logger)
            self._logger.error("       We'll continue with updating your configuration. You\n"
                               "       may be able to start your site after this, but it is\n"
                               "       recommended to remove the incompatible plugins soon.\n")

        # TODO: We are about to rewrite parts of the config. Would be better to be executable without
        # loading the configuration first (because the load_config() may miss some conversion logic
        # which is only known to cmk.update_config in the future).
        cmk.gui.config.load_config()
        cmk.gui.config.set_super_user()

    def _cleanup_version_specific_caches(self):
        # type: () -> None
        paths = [
            Path(cmk.utils.paths.include_cache_dir, "builtin"),
            Path(cmk.utils.paths.include_cache_dir, "local"),
            Path(cmk.utils.paths.precompiled_checks_dir, "builtin"),
            Path(cmk.utils.paths.precompiled_checks_dir, "local"),
        ]
        for base_dir in paths:
            try:
                for f in base_dir.iterdir():
                    f.unlink()
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise  # Do not fail on missing directories / files


def _show_failed_plugin_error(logger):
    logger.error("")
    logger.error("ERROR: Failed to load some GUI plugins. You will either have \n"
                 "       to remove or update them to be compatible with this \n"
                 "       Checkmk version.\n")


def main(args):
    # type: (List[str]) -> int
    arguments = parse_arguments(args)
    cmk.utils.log.setup_console_logging()
    cmk.utils.log.set_verbosity(arguments.verbose)
    logger = cmk.utils.log.get_logger("update_config")
    if arguments.debug:
        cmk.utils.debug.enable()
    logger.debug("parsed arguments: %s", arguments)

    try:
        UpdateConfig(logger, arguments).run()
    except MKIncompatiblePluginException:
        if arguments.debug:
            raise
        _show_failed_plugin_error(logger)
        logger.exception("       We can not continue updating your config. You\n"
                         "       will have to repair or remove your incompatible\n"
                         "       plugins and run \"cmk-update-config -v\" BEFORE\n"
                         "       starting your site again.\n\n")
        return 1

    except Exception:
        if arguments.debug:
            raise
        logger.exception("ERROR: Please repair this and run \"cmk-update-config -v\" "
                         "BEFORE starting the site again.")
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
