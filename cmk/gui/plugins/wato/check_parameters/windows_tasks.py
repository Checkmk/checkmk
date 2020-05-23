#!/usr/bin/python

# Author
# Antoine Scheffold
# antoinescheffold@gmail.com

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    ListOf,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_windows_tasks():
    return Tuple(
        title=_("Value Spec"),
        elements=[
         ListOf(
             Tuple(
                 title=_("Windows task exitcode definition"),
                 elements=[
                  TextAscii(
                            title=_("Exitcode: "),
                            help = _("Enter the exitcode as hex value, e.g. 0x00000000."),
                            ),
                  MonitoringState(
                            title = _("State for the exitcode: "),
                            default_value = 0,
                        ),
                  TextAscii(
                            title=_("Infotext: "),
                            help = _("This infotext will be shown in CheckMK. If there is already a text, you can leave this empty"),
                        ),
             ])
         ),
         MonitoringState(title = _("State if task not enabled: "),),
    ])



rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="windows_tasks_group",
        group=RulespecGroupCheckParametersApplications,
        match_type="first",
        parameter_valuespec=_parameter_valuespec_windows_tasks,
        title=lambda: _("Windows Tasks"),
    ))


