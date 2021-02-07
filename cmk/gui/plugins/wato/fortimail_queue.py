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

def _parameter_valuespec_fortimail_queue():
    return Dictionary(
        elements=[("queued_mails",
                   Tuple(title=_("Levels for Mail count"),
                         help=_("These levels make the check go warning or critical whenever the "
                                "<b>Mail amount</b> of the monitored Mail Queue is reached."),
                         elements=[
                             Integer(title=_("warning at"), unit=u"Mails", default_value=100),
                             Integer(title=_("critical at"), unit=u"Mails", default_value=200),
                         ]))])

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortimail_queue",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Queue Name"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fortimail_queue,
        title=lambda: _("Fortinet Mail Queue Info"),
    ))