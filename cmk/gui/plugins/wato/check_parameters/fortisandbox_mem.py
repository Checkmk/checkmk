# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

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


def _parameter_valuespec_fortisandbox_mem():
    return Dictionary(elements=[(
        "mem_usage",
        Tuple(title=_("Levels for Memory usage"),
              help=_("These levels make the check go warning or critical whenever the "
                     "<b>memory usage</b> of the monitored Fortinet Sandbox System is too high."),
              elements=[
                  Integer(title=_("warning at"), unit=u"%", default_value=80),
                  Integer(title=_("critical at"), unit=u"%", default_value=90),
              ]))])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortisandbox_mem",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=_parameter_valuespec_fortisandbox_mem,
        title=lambda: _("Fortinet Sandbox Memory usage"),
    ))
