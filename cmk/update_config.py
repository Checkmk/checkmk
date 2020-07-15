#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tool for updating Checkmk configuration files after version updates

This command is normally executed automatically at the end of "omd update" on
all sites and on remote sites after receiving a snapshot and does not need to
be called manually.",
"""

import re
import os
from pathlib import Path
import errno
from typing import List, Tuple, Any, Dict, Set
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
from cmk.utils.exceptions import MKGeneralException
import cmk.utils.paths
import cmk.utils
from cmk.utils.type_defs import UserId
import cmk.gui.pagetypes as pagetypes
import cmk.gui.visuals as visuals
from cmk.gui.plugins.views.utils import get_all_views
from cmk.gui.plugins.dashboard.utils import get_all_dashboards
import cmk.gui.watolib.tags  # pylint: disable=cmk-module-layer-violation
import cmk.gui.watolib.hosts_and_folders  # pylint: disable=cmk-module-layer-violation
import cmk.gui.watolib.rulesets  # pylint: disable=cmk-module-layer-violation
import cmk.gui.modules  # pylint: disable=cmk-module-layer-violation
import cmk.gui.config  # pylint: disable=cmk-module-layer-violation
import cmk.gui.utils  # pylint: disable=cmk-module-layer-violation
import cmk.gui.htmllib as htmllib  # pylint: disable=cmk-module-layer-violation
from cmk.gui.globals import AppContext, RequestContext  # pylint: disable=cmk-module-layer-violation
from cmk.gui.http import Request  # pylint: disable=cmk-module-layer-violation

import cmk.update_rrd_fs_names


# TODO: Better make our application available?
class DummyApplication:
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response


class UpdateConfig:
    def __init__(self, logger: logging.Logger, arguments: argparse.Namespace) -> None:
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
                try:
                    step_func()
                except Exception:
                    self._logger.log(VERBOSE, " + \"%s\" failed" % title, exc_info=True)

        self._logger.log(VERBOSE, "Done")

    def _steps(self):
        return [
            (self._rewrite_wato_tag_config, "Rewriting WATO tags"),
            (self._rewrite_wato_host_and_folder_config, "Rewriting WATO hosts and folders"),
            (self._rewrite_wato_rulesets, "Rewriting WATO rulesets"),
            (self._rewrite_autochecks, "Rewriting autochecks"),
            (self._cleanup_version_specific_caches, "Cleanup version specific caches"),
            (self._update_fs_used_name, "Migrating fs_used name"),
            (self._migrate_pagetype_topics_to_ids, "Migrate pagetype topics"),
        ]

    # FS_USED UPDATE DELETE THIS FOR CMK 1.8, THIS ONLY migrates 1.6->1.7
    def _update_fs_used_name(self):
        # Test if User migrated during 1.6 to new name fs_used. If so delete marker flag file
        old_config_flag = os.path.join(cmk.utils.paths.omd_root, 'etc/check_mk/conf.d/fs_cap.mk')
        if os.path.exists(old_config_flag):
            self._logger.log(VERBOSE, 'remove flag %s' % old_config_flag)
            os.remove(old_config_flag)

        check_df_includes_use_new_metric()
        cmk.update_rrd_fs_names.update()

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
        check_variables = cmk.base.config.get_check_variables()
        for autocheck_file in Path(cmk.utils.paths.autochecks_dir).glob("*.mk"):
            hostname = autocheck_file.stem
            try:
                autochecks = cmk.base.autochecks.parse_autochecks_file(
                    hostname,
                    cmk.base.config.service_description,
                    check_variables,
                )
            except MKGeneralException as exc:
                raise MKGeneralException(
                    "%s\nIf you encounter this error during the update process "
                    "you need to replace the the variable by its actual value, e.g. "
                    "replace `my_custom_levels` by `{'levels': (23, 42)}`." % exc)
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

    def _cleanup_version_specific_caches(self) -> None:
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

    def _migrate_pagetype_topics_to_ids(self):
        """Change all visuals / page types to use IDs as topics

        1.7 changed the topic from a free form user localizable string to an ID
        that references the builtin and user managable "pagetype_topics".

        Try to detect builtin or existing topics topics, reference them and
        also create missing topics and refernce them.

        Persist all the user visuals and page types after modification.
        """
        topic_created_for: Set[UserId] = set()
        pagetypes.PagetypeTopics.load()
        topics = pagetypes.PagetypeTopics.instances_dict()

        # Create the topics for all page types
        topic_created_for.update(self._migrate_pagetype_topics(topics))

        # And now do the same for all visuals (views, dashboards, reports)
        topic_created_for.update(self._migrate_all_visuals_topics(topics))

        # Now persist all added topics
        for user_id in topic_created_for:
            pagetypes.PagetypeTopics.save_user_instances(user_id)

    def _migrate_pagetype_topics(self, topics: Dict):
        topic_created_for: Set[UserId] = set()

        for page_type_cls in pagetypes.all_page_types().values():
            if not issubclass(page_type_cls, pagetypes.PageRenderer):
                continue

            page_type_cls.load()
            modified_user_instances = set()

            # First modify all instances in memory and remember which things have changed
            for instance in page_type_cls.instances():
                owner = instance.owner()
                instance_modified, topic_created = self._transform_pre_17_topic_to_id(
                    topics, instance.internal_representation())

                if instance_modified and owner:
                    modified_user_instances.add(owner)

                if topic_created and owner:
                    topic_created_for.add(owner)

            # Now persist all modified instances
            for user_id in modified_user_instances:
                page_type_cls.save_user_instances(user_id)

        return topic_created_for

    def _migrate_all_visuals_topics(self, topics: Dict):
        topic_created_for: Set[UserId] = set()

        # Views
        topic_created_for.update(
            self._migrate_visuals_topics(topics, visual_type="views", all_visuals=get_all_views()))

        # Dashboards
        topic_created_for.update(
            self._migrate_visuals_topics(topics,
                                         visual_type="dashboards",
                                         all_visuals=get_all_dashboards()))

        # Reports
        try:
            import cmk.gui.cee.reporting as reporting
        except ImportError:
            reporting = None  # type: ignore[assignment]

        if reporting:
            reporting.load_reports()
            topic_created_for.update(
                self._migrate_visuals_topics(topics,
                                             visual_type="dashboards",
                                             all_visuals=reporting.reports))

        return topic_created_for

    def _migrate_visuals_topics(self, topics, visual_type: str, all_visuals: Dict) -> Set[UserId]:
        topic_created_for: Set[UserId] = set()
        modified_user_instances: Set[UserId] = set()

        # First modify all instances in memory and remember which things have changed
        for (owner, _name), visual_spec in all_visuals.items():
            instance_modified, topic_created = self._transform_pre_17_topic_to_id(
                topics, visual_spec)

            if instance_modified and owner:
                modified_user_instances.add(owner)

            if topic_created and owner:
                topic_created_for.add(owner)

        # Now persist all modified instances
        for user_id in modified_user_instances:
            visuals.save(visual_type, all_visuals, user_id)

        return topic_created_for

    def _transform_pre_17_topic_to_id(self, topics: Dict, spec: Dict[str,
                                                                     Any]) -> Tuple[bool, bool]:
        topic = spec["topic"] or ""
        topic_key = (spec["owner"], topic)
        name = _id_from_title(topic)
        name_key = (spec["owner"], topic)

        topics_by_title = {v.title(): k for k, v in topics.items()}

        if ("", topic) in topics:
            # No need to transform. Found a builtin topic which has the current topic
            # as ID
            return False, False

        if ("", name) in topics:
            # Found a builtin topic matching the generated name, assume we have a match
            spec["topic"] = name
            return True, False

        if name_key in topics:
            # Found a custom topic matching the generated name, assume we have a match
            spec["topic"] = name
            return True, False

        if topic_key in topics:
            # No need to transform. Found a topic which has the current topic as ID
            return False, False

        if topic in topics_by_title and topics_by_title[topic][0] in ["", spec["owner"]]:
            # Found an existing topic which title exactly matches the current topic attribute and which
            # is either owned by the same user as the spec or builtin and accessible
            spec["topic"] = topics_by_title[topic][1]
            return True, False

        # Found no match: Create a topic for this spec and use it
        # Use same owner and visibility settings as the original
        pagetypes.PagetypeTopics.add_instance(
            (spec["owner"], name),
            pagetypes.PagetypeTopics({
                "name": name,
                "title": topic,
                "description": "",
                "public": spec["public"],
                "icon_name": "topic_unknown",
                "sort_index": 99,
                "owner": spec["owner"],
            }),
        )

        spec["topic"] = name
        return True, True


def _id_from_title(title):
    return re.sub("[^-a-zA-Z0-9_]+", "", title.lower().replace(" ", "_"))


def main(args: List[str]) -> int:
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


def parse_arguments(args: List[str]) -> argparse.Namespace:
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
