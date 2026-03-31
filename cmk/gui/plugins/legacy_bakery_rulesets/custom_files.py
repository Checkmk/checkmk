#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from pathlib import Path

import cmk.utils.paths
import cmk.utils.render
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupMonitoringAgentsGenericOptions,
)
from cmk.gui.valuespec import ListChoice, Transform
from cmk.utils.rulesets.definition import RuleGroup


def custom_file_base_path() -> Path:
    return cmk.utils.paths.local_agents_dir / "custom"


def _agent_config_custom_files_get_custom_files_choices() -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = []
    custom_dir = custom_file_base_path()

    if not custom_dir.exists():
        return choices

    for entry in custom_dir.glob("*"):
        if entry.is_dir():
            folder = str(entry.relative_to(custom_dir))
            choices.append((folder, folder))

    return sorted(choices)


def _valuespec_agent_config_custom_files() -> Transform:
    return Transform(
        valuespec=ListChoice(
            title=_("Deploy custom files with agent"),
            choices=_agent_config_custom_files_get_custom_files_choices,
        ),
        help=_(
            "This rule provides a simple way to add files to agent bakery packages without the need"
            " to write a bakery plugin.<br>"
            "<i>Custom files</i> are organized in folders under <tt>{omd_root}/local/share/check_mk/agents/custom</tt>.<br>"
            "To add a set of custom files to the agent, please create a subfolder there with a meaningful"
            " name of your choice.<br>"
            "Added folders will be shown in this rule for activation.<br>"
            "<br>"
            "Since the agent installation paths are customizable by other rules, the file structure"
            " below these sets doesn't resemble directly to the agent installation.<br>"
            "Instead, the structure is organized in <i>logical paths</i> that map to certain target folders"
            " in the final agent installation.<br>"
            "Files placed under a <i>logical path</i> will also apply the ownership and permissions"
            " based on the agent installation.<br>"
            "<br>"
            "<h2>Mapping under Linux/UNIX:</h2><br>"
            "Ownership and permissions on the Checkmk site's file structure don't matter, with one"
            " exception: Executable flags on files will be preserved.<br>"
            "<br>"
            "Overview of <i>logical paths</i> and their targets:"
            "<ul>"
            "<li><tt>lib</tt>: Internal agent files (<tt>MK_LIBDIR</tt> on the host)</li>"
            "<li><tt>bin</tt>: Executables (<tt>MK_BIN</tt> on the host)</li>"
            "<li><tt>var</tt>: Runtime data (<tt>MK_VARDIR</tt> on the host)</li>"
            "<li><tt>config</tt>: Configuration files (<tt>MK_CONFDIR</tt> on the host)</li>"
            "<li><tt>lib/plugins</tt>: Agent plugins</li>"
            "<li><tt>lib/local</tt>: Local checks</li>"
            "</ul>"
            "<b>Example</b>: Let's say you place the following files:<br>"
            "<tt>{omd_root}/local/share/check_mk/agents/custom/myset/bin/some_executable</tt><br>"
            "<tt>{omd_root}/local/share/check_mk/agents/custom/myset/lib/local/my_local_check</tt><br>"
            "<tt>{omd_root}/local/share/check_mk/agents/custom/myset/some_file</tt><br>"
            "and activate <i>myset</i> in this rule.<br>"
            "Then, the following files will be deployed to target hosts when not further"
            " configuring agent paths:<br>"
            "<tt>/usr/bin/some_executable</tt><br>"
            "<tt>/usr/lib/check_mk_agent/local/my_local_check</tt><br>"
            "<tt>/usr/lib/check_mk_agent/some_file</tt><br>"
            "When activating the single directory deployment in the <i>Customize agent package</i>"
            " ruleset:<br>"
            "<tt>/opt/checkmk/agent/default/package/bin/some_executable</tt><br>"
            "<tt>/opt/checkmk/agent/default/package/local/my_local_check</tt><br>"
            "<tt>/opt/checkmk/agent/default/package/some_file</tt><br>"
            "<br>"
            "<h2>Mapping under Windows:</h2><br>"
            "Other than the Linux/UNIX agent installation, the Windows agent installation uses fixed paths,"
            " so there is also a fixed mapping from logical path to folders on the host.<br>"
            "Like other agent plugins, custom files install to the working directory under"
            " <tt>C:\\ProgramData\\checkmk\\agent</tt>:"
            "<ul>"
            "<li><tt>lib</tt>: <tt>..\\agent</tt></li>"
            "<li><tt>bin</tt>: <tt>..\\agent\\bin</tt></li>"
            "<li><tt>var</tt>: <tt>..\\agent</tt></li>"
            "<li><tt>config</tt>: <tt>..\\agent\\config</tt></li>"
            "<li><tt>lib/plugins</tt>: <tt>..\\agent\\plugins</tt></li>"
            "<li><tt>lib/local</tt>: <tt>..\\agent\\local</tt></li>"
            "</ul>"
        ).format(omd_root=cmk.utils.paths.omd_root),
        # If a custom dir gets deleted, we also remove the configured path
        to_valuespec=lambda choices: [
            x for x in choices if (x, x) in _agent_config_custom_files_get_custom_files_choices()
        ],
        from_valuespec=lambda x: x,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsGenericOptions,
        match_type="list",
        name=RuleGroup.AgentConfig("custom_files"),
        valuespec=_valuespec_agent_config_custom_files,
    )
)
