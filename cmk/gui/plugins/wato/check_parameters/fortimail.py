#author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_fortimail_system():
    return Dictionary(
        elements=[("mail_sysload",
                   Tuple(title=_("Levels for system load"),
                         help=_("These levels make the check go warning or critical whenever the "
                                "<b>system load</b> of the monitored Fortinet Mail is too high."),
                         elements=[
                             Integer(title=_("warning at"), unit=u"%", default_value=80),
                             Integer(title=_("critical at"), unit=u"%", default_value=90),
                         ]))])


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


def _parameter_valuespec_fortimail():
    return Dictionary(
        elements=[("mcount",
                   Tuple(title=_("Levels for Mail amount"),
                         help=_("These levels make the check go warning or critical whenever the "
                                "<b>Mail amount</b> of the monitored Mail Queue is reached."),
                         elements=[
                             Integer(title=_("warning at"), unit=u"Mails", default_value=100),
                             Integer(title=_("critical at"), unit=u"Mails", default_value=200),
                         ]))])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortimail_sysload",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=_parameter_valuespec_fortimail_system,
        title=lambda: _("Fortinet Mail System Load"),
    ))

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortimail_disk",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=_parameter_valuespec_fortimail_disk,
        title=lambda: _("Fortinet Mail Disk usage"),
    ))

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortimail",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Queue Name"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fortimail,
        title=lambda: _("Fortinet Mail Queue Info"),
    ))
