#author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)

def _parameter_valuespec_fortigate_ips():
    return Dictionary(elements=[(
        "intrusions",
        Tuple(title=_("Detected intrusions/5min"),
              help=_("These levels make the check go warning or critical whenever the "
                     "<b>count of Detected intrusions/s</b> of the monitored Fortigate System is too high."),
              elements=[
                  Integer(title=_("warning at"), unit=u"Intrusions/5min", default_value=100),
                  Integer(title=_("critical at"), unit=u"Intrusions/5min", default_value=300),
              ]))])

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortigate_ips",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("IPS Number"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fortigate_ips,
        title=lambda: _("Fortinet FortiGate IPS Intrusions"),
    ))
