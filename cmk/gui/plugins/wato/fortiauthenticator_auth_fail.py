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


def _parameter_valuespec_fortiauthenticator_auth_fail():
    return Dictionary(elements=[(
        "auth_fails",
        Tuple(
            title=_("Failure count"),
            help=
            _("These levels make the check go warning or critical whenever the "
              "<b>count of Authentication Failures within 5 Minutes</b> of the monitored Fortinet Authentication System is too high."
             ),
            elements=[
                Integer(title=_("warning at"), unit=u"Failures", default_value=100),
                Integer(title=_("critical at"), unit=u"Failures", default_value=200),
            ]))])


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="fortiauthenticator_auth_fail",
        group=RulespecGroupCheckParametersNetworking,
        parameter_valuespec=_parameter_valuespec_fortiauthenticator_auth_fail,
        title=lambda: _("Fortinet Authenticator Failure"),
    ))
