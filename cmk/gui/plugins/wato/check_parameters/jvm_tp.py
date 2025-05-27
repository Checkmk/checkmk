#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Integer,
    Migrate,
    TextInput,
    Tuple,
)


def _item_spec_jvm_tp() -> TextInput:
    return TextInput(
        title=_("Name of the virtual machine and/or<br>threadpool"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def _levels(unit: str = "") -> Tuple:
    return Tuple(
        elements=[
            Integer(title=_("Warning at"), unit=unit),
            Integer(title=_("Critical at"), unit=unit),
        ],
    )


def _migrate(x: tuple[int, int] | tuple[str, tuple[int, int]]) -> tuple[str, tuple[int, int]]:
    return (
        x if isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], str) else ("percentage", x)
    )


def _parameter_valuespec_jvm_tp() -> Dictionary:
    return Dictionary(
        help=_("This ruleset also covers Tomcat, Jolokia and JMX. "),
        elements=[
            (
                "currentThreadCount",
                Migrate(
                    valuespec=CascadingDropdown(
                        title=_("Current thread count levels"),
                        choices=[
                            (
                                "percentage",
                                _("Percentage levels of current thread count in threadpool"),
                                _levels(unit="%"),
                            ),
                            (
                                "absolute",
                                _("Number of current thread count in threadpool"),
                                _levels(),
                            ),
                        ],
                    ),
                    migrate=_migrate,
                ),
            ),
            (
                "currentThreadsBusy",
                Migrate(
                    valuespec=CascadingDropdown(
                        title=_("Current threads busy levels"),
                        choices=[
                            (
                                "percentage",
                                _("Percentage of current threads busy in threadpool"),
                                _levels(unit="%"),
                            ),
                            (
                                "absolute",
                                _("Number of current threads busy in threadpool"),
                                _levels(),
                            ),
                        ],
                    ),
                    migrate=_migrate,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_tp",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_tp,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_tp,
        title=lambda: _("JVM tomcat threadpool levels"),
    )
)
