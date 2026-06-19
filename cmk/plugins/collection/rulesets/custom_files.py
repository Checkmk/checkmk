#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    List,
    String,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "folders" in value:
        return value
    if isinstance(value, list):
        return {"folders": value}
    raise ValueError(f"Unexpected value: {value!r}")


def _valuespec_agent_config_custom_files() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This rule provides a simple way to add files to agent bakery packages without the need"
            " to write a bakery plug-in.<br>"
            "<i>Custom files</i> are organized in folders under"
            " <tt>&lt;site_root&gt;/local/share/check_mk/agents/custom</tt>.<br>"
            "To add a set of custom files to the agent, please create a subfolder there with a meaningful"
            " name of your choice and enter the folder name here.<br>"
            "<br>"
            "Since the agent installation paths are customizable by other rules, the file structure"
            " below these sets doesn't resemble directly to the agent installation.<br>"
            "Instead, the structure is organized in <i>logical paths</i> that map to certain target folders"
            " in the final agent installation.<br>"
            "Files placed under a <i>logical path</i> will also apply the ownership and permissions"
            " based on the agent installation.<br>"
            "<br>"
            "<h2>Mapping under Linux/Unix:</h2><br>"
            "Ownership and permissions on the Checkmk site's file structure don't matter, with one"
            " exception: Executable flags on files will be preserved.<br>"
            "<br>"
            "Overview of <i>logical paths</i> and their targets:"
            "<ul>"
            "<li><tt>lib</tt>: Internal agent files (<tt>MK_LIBDIR</tt> on the host)</li>"
            "<li><tt>bin</tt>: Executables (<tt>MK_BIN</tt> on the host)</li>"
            "<li><tt>var</tt>: Runtime data (<tt>MK_VARDIR</tt> on the host)</li>"
            "<li><tt>config</tt>: Configuration files (<tt>MK_CONFDIR</tt> on the host)</li>"
            "<li><tt>lib/plugins</tt>: Agent plug-ins</li>"
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
            " rule set:<br>"
            "<tt>/opt/checkmk/agent/default/package/bin/some_executable</tt><br>"
            "<tt>/opt/checkmk/agent/default/package/local/my_local_check</tt><br>"
            "<tt>/opt/checkmk/agent/default/package/some_file</tt><br>"
            "<br>"
            "<h2>Mapping under Windows:</h2><br>"
            "Other than the Linux/Unix agent installation, the Windows agent installation uses fixed paths,"
            " so there is also a fixed mapping from logical path to folders on the host.<br>"
            "Like other agent plug-ins, custom files install to the working directory under"
            " <tt>C:\\ProgramData\\checkmk\\agent</tt>:"
            "<ul>"
            "<li><tt>lib</tt>: <tt>..\\agent</tt></li>"
            "<li><tt>bin</tt>: <tt>..\\agent\\bin</tt></li>"
            "<li><tt>var</tt>: <tt>..\\agent</tt></li>"
            "<li><tt>config</tt>: <tt>..\\agent\\config</tt></li>"
            "<li><tt>lib/plugins</tt>: <tt>..\\agent\\plugins</tt></li>"
            "<li><tt>lib/local</tt>: <tt>..\\agent\\local</tt></li>"
            "</ul>"
        ),
        elements={
            "folders": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("Custom file folders to deploy"),
                    element_template=String(),
                ),
            ),
        },
        migrate=migrate,
    )


rule_spec_custom_files = AgentConfig(
    title=Title("Deploy custom files with agent"),
    name="custom_files",
    topic=Topic.GENERAL,
    parameter_form=_valuespec_agent_config_custom_files,
)
