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


def _parameter_valuespec_fortimail_disk():
    return Dictionary(elements=[(
        "mail_disk_usage",
        Tuple(title=_("Levels for mail disk usage"),
              help=_("These levels make the check go warning or critical whenever the "
                     "<b>used mail disk</b> of the monitored Fortinet Mail is too high."),
              elements=[
                  Integer(title=_("warning at"), unit=u"%", default_value=80),
                  Integer(title=_("critical at"), unit=u"%", default_value=90),
              ]))])
    

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortimail_disk",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=_parameter_valuespec_fortimail_disk,
        title=lambda: _("Fortinet Mail Disk usage"),
    ))
