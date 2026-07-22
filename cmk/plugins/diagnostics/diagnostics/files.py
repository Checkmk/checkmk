#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Collect Checkmk configuration files, log files and the Apache configuration

Each plugin bundles only files of its declared sensitivity; users select per
topic how sensitive the packed files may be. Configuration and log files are
redacted (passwords) and sanitized (site configuration secrets), so they are
always generated content; the Apache configuration is copied verbatim.
"""

from collections.abc import Iterable
from functools import partial
from pathlib import Path, PurePosixPath

# TODO: FILE_MAP_* move into this family's lib once the GUI is migrated.
from cmk.diagnostics.engine import FILE_MAP_CONFIG, FILE_MAP_LOG
from cmk.diagnostics.internal import (
    CollectContext,
    DiagnosticsPlugin,
    DumpItem,
    Help,
    Sensitivity,
)
from cmk.plugins.diagnostics.lib.files import collect_bucket, walk_verbatim
from cmk.plugins.diagnostics.lib.topics import TOPIC_CONFIGURATION, TOPIC_LOGS


def _collect_apache_config(context: CollectContext) -> Iterable[DumpItem]:
    for directory in ("/etc/apache2", "/etc/httpd", "/opt/omd/apache"):
        root = Path(directory)
        yield from walk_verbatim(root, PurePosixPath("os_root") / root.relative_to("/"))
    rel_root = context.omd_root / "etc/apache"
    yield from walk_verbatim(rel_root, PurePosixPath("etc/apache"))


diagnostics_plugin_config_files_low = DiagnosticsPlugin(
    name="config_files_low",
    description=Help(
        "Configuration files ('*.mk' or '*.conf') below etc/check_mk"
        " that are classified as insensitive"
    ),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_CONFIGURATION,
    handler=partial(collect_bucket, file_map=FILE_MAP_CONFIG, bucket=Sensitivity.LOW),
)

diagnostics_plugin_config_files_medium = DiagnosticsPlugin(
    name="config_files_medium",
    description=Help(
        "Configuration files ('*.mk' or '*.conf') below etc/check_mk that may include"
        " sensitive data like IP addresses, host names, usernames or mail addresses"
    ),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_CONFIGURATION,
    handler=partial(collect_bucket, file_map=FILE_MAP_CONFIG, bucket=Sensitivity.MEDIUM),
)

diagnostics_plugin_config_files_high = DiagnosticsPlugin(
    name="config_files_high",
    description=Help(
        "Configuration files ('*.mk' or '*.conf') below etc/check_mk that may include"
        " highly sensitive data like passwords, including all files without a"
        " sensitivity classification"
    ),
    sensitivity=Sensitivity.HIGH,
    topic=TOPIC_CONFIGURATION,
    handler=partial(collect_bucket, file_map=FILE_MAP_CONFIG, bucket=Sensitivity.HIGH),
)

diagnostics_plugin_apache_config = DiagnosticsPlugin(
    name="apache_config",
    description=Help("The Apache configuration of the operating system and the site"),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_CONFIGURATION,
    handler=_collect_apache_config,
)

diagnostics_plugin_log_files_low = DiagnosticsPlugin(
    name="log_files_low",
    description=Help(
        "Log files ('*.log' or '*.state') below var/log that are classified as insensitive"
    ),
    sensitivity=Sensitivity.LOW,
    topic=TOPIC_LOGS,
    handler=partial(collect_bucket, file_map=FILE_MAP_LOG, bucket=Sensitivity.LOW),
)

diagnostics_plugin_log_files_medium = DiagnosticsPlugin(
    name="log_files_medium",
    description=Help(
        "Log files ('*.log' or '*.state') below var/log that may include sensitive"
        " data like IP addresses, host names, usernames or mail addresses"
    ),
    sensitivity=Sensitivity.MEDIUM,
    topic=TOPIC_LOGS,
    handler=partial(collect_bucket, file_map=FILE_MAP_LOG, bucket=Sensitivity.MEDIUM),
)

diagnostics_plugin_log_files_high = DiagnosticsPlugin(
    name="log_files_high",
    description=Help(
        "Log files ('*.log' or '*.state') below var/log that may include highly"
        " sensitive data, including all files without a sensitivity classification"
    ),
    sensitivity=Sensitivity.HIGH,
    topic=TOPIC_LOGS,
    handler=partial(collect_bucket, file_map=FILE_MAP_LOG, bucket=Sensitivity.HIGH),
)
