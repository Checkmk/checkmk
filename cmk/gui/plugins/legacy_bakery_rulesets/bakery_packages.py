#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "You can use these options to tune the way packages are baked for your hosts which may "
            "have a positive impact on the performance of the baking procedure. "
            "Defaults to bake for all platforms with no compression."
        ),
        elements={
            "selection": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Select packages"),
                    help_text=Help(
                        "Explicitly select packages to be baked. "
                        "If this rule entry is not activated, all packages are baked."
                    ),
                    elements=[
                        MultipleChoiceElement(name="linux_deb", title=Title("Linux: DPKG (.deb)")),
                        MultipleChoiceElement(name="linux_rpm", title=Title("Linux: RPM (.rpm)")),
                        MultipleChoiceElement(
                            name="linux_tgz", title=Title("Linux: TGZ (.tar.gz)")
                        ),
                        MultipleChoiceElement(
                            name="solaris_pkg", title=Title("Solaris: PKG (.pkg)")
                        ),
                        MultipleChoiceElement(
                            name="solaris_tgz", title=Title("Solaris: TGZ (.tar.gz)")
                        ),
                        MultipleChoiceElement(name="aix_tgz", title=Title("AIX: TGZ (.tar.gz)")),
                        MultipleChoiceElement(
                            name="windows_msi", title=Title("Windows: MSI (.msi)")
                        ),
                    ],
                    show_toggle_all=True,
                ),
            ),
            "compression": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Apply compression to agent packages"),
                    help_text=Help(
                        "When activated, the Agent Bakery will compress most of the agent packages. "
                        "The compression applies to .deb packages, .rpm packages and to all "
                        ".tar.gz packages that result from baking agents. "
                        "Note: In order to avoid name changes in packages, the uncompressed TAR "
                        "packages also have a suffix of .tar.gz. Technically, they are compressed "
                        "using gzip with a compression level of 0."
                        "It's not recommended to activate compression unless you want to deploy "
                        "large files resulting from custom files or your own bakery plugins. "
                        "All large files (larger than a few kb, mainly the agent updater and the "
                        "agent controller) provided by Checkmk are precompressed and won't benefit "
                        "from enabling compression."
                    ),
                    label=Label("Apply compression"),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )


rule_spec_bakery_packages = AgentConfig(
    name="bakery_packages",
    title=Title("Agent Bakery packages"),
    topic=Topic.GENERAL,
    parameter_form=_form_spec,
)
