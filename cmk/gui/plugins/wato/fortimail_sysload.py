#author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_fortimail_sysload():
    return Dictionary(
        elements=[("mail_sysload",
                   Tuple(title=_("Levels for system load"),
                         help=_("These levels make the check go warning or critical whenever the "
                                "<b>system load</b> of the monitored Fortinet Mail is too high."),
                         elements=[
                             Integer(title=_("warning at"), unit=u"%", default_value=90),
                             Integer(title=_("critical at"), unit=u"%", default_value=95),
                         ]))])
    

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortimail_sysload",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=_parameter_valuespec_fortimail_sysload,
        title=lambda: _("Fortinet Mail System Load"),
    ))
