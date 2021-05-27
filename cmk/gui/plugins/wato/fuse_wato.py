from cmk.gui.plugins.wato import (
    RulespecGroup,
    RulespecSubGroup,
    rulespec_group_registry,
    rulespec_registry,
    HostRulespec
)


@rulespec_group_registry.register
class RulespecGroupDatasourcePrograms(RulespecGroup):
    @property
    def name(self):
        return "datasource_programs"

    @property
    def title(self):
        return _("Other integrations")

    @property
    def help(self):
        return _("Integrate platforms using special agents, e.g. SAP R/3")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsApps(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "apps"

    @property
    def title(self):
        return _("Applications")


def _valuespec_special_agents_fuse():
    return Dictionary(
        title=_("Fuse Management Central"),
        help=
        _("This rule set selects the special agent for Fuse Management Central "
          "instead of the normal Check_MK agent and allows monitoring via REST API."),
        elements=[
            ("user", TextAscii(title=("Username"), allow_empty=False)),
            ("password", Password(title=("Password"), allow_empty=False)),
            ("url", TextAscii(title=("Alerts API Endpoint"), allow_empty=False))
        ],
        required_keys=["user","password","url"]
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        help_func=lambda: _("This rule selects the special agent for Fuse Management Central."),
        name="special_agents:fuse",
        title=lambda: _("Fuse Management Central"),
        valuespec=_valuespec_special_agents_fuse,
    ))
