#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.generic_agent_options.rulesets._topic import (
    TOPIC_LINUX_UNIX_AGENT_OPTIONS,
)
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import Dictionary
from cmk.rulesets.v1.rule_specs import AgentConfig


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Hosts that match this rule keep the classic file deployment. The classic file"
            " deployment distributes the agent files over several directories, such as"
            " <tt>/usr/bin</tt>, <tt>/etc/check_mk</tt> and <tt>/var/lib/check_mk_agent</tt>."
            " The rule sets <i>Installation paths for agent files</i> and <i>Run agent as"
            " non-root user</i> apply only to these hosts. As an exception, the migration to"
            " the single-directory deployment takes the old directory for variable data from"
            " <i>Installation paths for agent files</i>. Keep the rules of <i>Installation"
            " paths for agent files</i> until the migrated hosts have installed their new"
            " agent package.<br>"
            "The rule set <i>Customize agent package</i> takes precedence over this rule set."
            " A host that matches both gets the single-directory deployment.<br>"
            "Hosts without a rule get the single-directory deployment. To move hosts, narrow"
            " the conditions of this rule, delete the rule, or add a rule <i>Customize agent"
            " package</i> for them.<br>"
            "Checkmk 3.1 will remove the classic file deployment."
        ),
        elements={},
    )


rule_spec_classic_file_deployment = AgentConfig(
    title=Title("Use classic file deployment"),
    name="classic_file_deployment",
    topic=TOPIC_LINUX_UNIX_AGENT_OPTIONS,
    parameter_form=_form_spec,
    is_deprecated=True,
)
