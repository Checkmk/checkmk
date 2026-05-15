#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic

_ABSOLUTE_PATH_PATTERN = re.compile(r"^(/|(/[^/]+)+)$")
_ABSOLUTE_PATH_VALIDATOR = validators.MatchRegex(
    _ABSOLUTE_PATH_PATTERN,
    Message("Please enter a valid absolute pathname with / as a path separator."),
)


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "The agent installation path configuration now simplifies to one single directory,"
            " which can be configured with the new <i>Customize agent package</i> rule set."
            "<br>When configuring <i>Customize agent package</i>, matching rules from"
            " this rule set will be ignored."
            "<br><b>Note</b>: When updating agents to the new directory structure, please keep"
            " this rule set until the agent update is done. The agent package will read the"
            " old installation paths to migrate your files to the new directory structure."
        ),
        elements={
            "bin": DictElement(
                parameter_form=String(
                    title=Title("Directory for binaries (executables)"),
                    help_text=Help(
                        "In this directory will be installed <tt>check_mk_agent</tt>,"
                        " <tt>waitmax</tt> and possibly other binaries that are needed"
                        " by the agent."
                    ),
                    prefill=DefaultValue("/usr/bin"),
                    custom_validate=(_ABSOLUTE_PATH_VALIDATOR,),
                ),
            ),
            "config": DictElement(
                parameter_form=String(
                    title=Title("Directory for configuration files"),
                    prefill=DefaultValue("/etc/check_mk"),
                    custom_validate=(_ABSOLUTE_PATH_VALIDATOR,),
                ),
            ),
            "lib": DictElement(
                parameter_form=String(
                    title=Title("Base directory for plug-ins and local"),
                    prefill=DefaultValue("/usr/lib/check_mk_agent"),
                    custom_validate=(_ABSOLUTE_PATH_VALIDATOR,),
                ),
            ),
            "var": DictElement(
                parameter_form=String(
                    title=Title("Base directory for variable data (caches, state files)"),
                    help_text=Help(
                        "If you change this paths away from its default then the package "
                        "will <b>not</b> delete the contents of that directory when uninstalling."
                    ),
                    prefill=DefaultValue("/var/lib/check_mk_agent"),
                    custom_validate=(_ABSOLUTE_PATH_VALIDATOR,),
                ),
            ),
            "tmp": DictElement(
                parameter_form=String(
                    title=Title(
                        "Directory for storage of temporary data (set TMPDIR environment variable)"
                    ),
                    help_text=Help(
                        "Some agent commands or plug-ins may follow the environment variable"
                        " TMPDIR for storage of temporary files."
                        " For some reasons, you might want to adapt this path."
                        ' Namely, the agent updater won\'t work with a "/tmp" dir that'
                        ' is mounted with a "noexec"-flag. Please note that the'
                        " Checkmk Agent does no automatic cleaning on this custom path."
                    ),
                    custom_validate=(_ABSOLUTE_PATH_VALIDATOR,),
                ),
            ),
        },
    )


rule_spec_agent_paths = AgentConfig(
    title=Title("Installation paths for agent files (Linux, Unix)"),
    name="agent_paths",
    topic=Topic.OPERATING_SYSTEM,
    parameter_form=_form_spec,
    is_deprecated=True,
)
