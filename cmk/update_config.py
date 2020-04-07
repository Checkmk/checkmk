#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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

import re
import os
import sys

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path

import subprocess
import errno
from typing import List  # pylint: disable=unused-import
import argparse
import logging
from werkzeug.test import create_environ

# This special script needs persistence and conversion code from different
# places of Checkmk. We may centralize the conversion and move the persistance
# to a specific layer in the future, but for the the moment we need to deal
# with it.
import cmk.base.autochecks  # pylint: disable=cmk-module-layer-violation
import cmk.base.config  # pylint: disable=cmk-module-layer-violation

import cmk.utils.log as log
from cmk.utils.log import VERBOSE
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils
import cmk.gui.watolib.tags  # pylint: disable=cmk-module-layer-violation
import cmk.gui.watolib.hosts_and_folders  # pylint: disable=cmk-module-layer-violation
import cmk.gui.watolib.rulesets  # pylint: disable=cmk-module-layer-violation
import cmk.gui.modules  # pylint: disable=cmk-module-layer-violation
import cmk.gui.config  # pylint: disable=cmk-module-layer-violation
import cmk.gui.utils  # pylint: disable=cmk-module-layer-violation
import cmk.gui.htmllib as htmllib  # pylint: disable=cmk-module-layer-violation
from cmk.gui.globals import AppContext, RequestContext  # pylint: disable=cmk-module-layer-violation
from cmk.gui.http import Request  # pylint: disable=cmk-module-layer-violation


# TODO: Better make our application available?
class DummyApplication(object):
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response


class UpdateConfig(object):
    def __init__(self, logger, arguments):
        # type: (logging.Logger, argparse.Namespace) -> None
        super(UpdateConfig, self).__init__()
        self._arguments = arguments
        self._logger = logger
        # TODO: Fix this cruel hack caused by our funny mix of GUI + console
        # stuff. Currently, we just move the console handler to the top, so
        # both worlds are happy. We really, really need to split business logic
        # from presentation code... :-/
        if log.logger.handlers:
            console_handler = log.logger.handlers[0]
            del log.logger.handlers[:]
            logging.getLogger().addHandler(console_handler)

    def run(self):
        self._logger.log(VERBOSE, "Initializing application...")
        environ = dict(create_environ(), REQUEST_URI='')

        this_html = htmllib.html(Request(environ))
        # Currently the htmllib.html constructor enables the timeout by default. This side effect
        # should really be cleaned up.
        this_html.disable_request_timeout()

        with AppContext(DummyApplication(environ, None)), \
                RequestContext(this_html):
            self._initialize_gui_environment()

            self._logger.log(VERBOSE, "Updating Checkmk configuration...")
            for step_func, title in self._steps():
                self._logger.log(VERBOSE, " + %s..." % title)
                step_func()

        self._logger.log(VERBOSE, "Done")

    def _steps(self):
        return [
            (self._rewrite_wato_tag_config, "Rewriting WATO tags"),
            (self._rewrite_wato_host_and_folder_config, "Rewriting WATO hosts and folders"),
            (self._rewrite_wato_rulesets, "Rewriting WATO rulesets"),
            (self._rewrite_autochecks, "Rewriting autochecks"),
            (self._cleanup_version_specific_caches, "Cleanup version specific caches"),
            (self._update_fs_used_name, "Migrating fs_used name"),
        ]

    # FS_USED UPDATE DELETE THIS FOR CMK 1.8, THIS ONLY migrates 1.6->1.7
    def _update_fs_used_name(self):
        # Test if User migrated during 1.6 to new name fs_used. If so delete marker flag file
        old_config_flag = os.path.join(cmk.utils.paths.omd_root, 'etc/check_mk/conf.d/fs_cap.mk')
        if os.path.exists(old_config_flag):
            self._logger.log(VERBOSE, 'remove flag %s' % old_config_flag)
            os.remove(old_config_flag)

        check_df_includes_use_new_metric()

        # TODO: Inline update_rrd_fs_names once GUI and this script have been migrated to Python 3
        ps = subprocess.Popen(
            ['python3',
             os.path.join(cmk.utils.paths.lib_dir, 'python/cmk/update_rrd_fs_names.py')],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        for line in iter(ps.stderr.readline, b''):
            self._logger.log(VERBOSE, line.strip())
        self._logger.log(VERBOSE, ps.stdout.read())

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
            autochecks = cmk.base.autochecks.parse_autochecks_file(
                hostname, cmk.base.config.service_description)
            cmk.base.autochecks.save_autochecks_file(hostname, autochecks)

    def _rewrite_wato_rulesets(self):
        all_rulesets = cmk.gui.watolib.rulesets.AllRulesets()
        all_rulesets.load()
        all_rulesets.save()

    def _initialize_gui_environment(self):
        self._logger.log(VERBOSE, "Loading GUI plugins...")
        cmk.gui.modules.load_all_plugins()
        failed_plugins = cmk.gui.utils.get_failed_plugins()

        if failed_plugins:
            self._logger.error("")
            self._logger.error("ERROR: Failed to load some GUI plugins. You will either have \n"
                               "       to remove or update them to be compatible with this \n"
                               "       Checkmk version.")
            self._logger.error("")

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


def main(args):
    # type: (List[str]) -> int
    arguments = parse_arguments(args)
    log.setup_console_logging()
    log.logger.setLevel(log.verbosity_to_log_level(arguments.verbose))
    logger = logging.getLogger("cmk.update_config")
    if arguments.debug:
        cmk.utils.debug.enable()
    logger.debug("parsed arguments: %s", arguments)

    try:
        UpdateConfig(logger, arguments).run()
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

    return p.parse_args(args)


# RRD migration cleaups


def check_df_includes_use_new_metric():
    "Check that df.include files can return fs_used metric name"
    df_file = cmk.utils.paths.local_checks_dir / 'df.include'
    if df_file.exists():
        with df_file.open('r') as fid:
            r = fid.read()
            mat = re.search('fs_used', r, re.M)
            if not mat:
                msg = ('source: %s\n Returns the wrong perfdata\n' % df_file +
                       'Checkmk 1.7 requires Filesystem check plugins to deliver '
                       '"Used filesystem space" perfdata under the metric name fs_used. '
                       'Your local extension pluging seems to be using the old convention '
                       'of mountpoints as the metric name. Please update your include file '
                       'to match our reference implementation.')
                raise RuntimeError(msg)
