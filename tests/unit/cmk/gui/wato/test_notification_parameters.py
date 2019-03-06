# Triggers plugin loading of plugins.wato which registers all the plugins
import cmk.gui.wato  # pylint: disable=unused-import
import cmk.gui.plugins.wato.utils as utils
from cmk.gui.valuespec import Dictionary
import cmk.gui.watolib.rulespecs as rulespecs

expected_plugins = [
    'asciimail',
    'jira_issues',
    'mail',
    'mkeventd',
    'pagerduty',
    'pushover',
    'slack',
    'spectrum',
    'victorops',
]


def test_registered_notification_parameters():
    registered_plugins = sorted(utils.notification_parameter_registry.keys())
    assert registered_plugins == sorted(expected_plugins)


def test_register_legacy_notification_parameters(monkeypatch):
    monkeypatch.setattr(utils, "notification_parameter_registry",
                        utils.NotificationParameterRegistry())
    rulespec_group_registry = rulespecs.RulespecGroupRegistry()
    monkeypatch.setattr(rulespecs, "rulespec_group_registry", rulespec_group_registry)
    monkeypatch.setattr(rulespecs, "rulespec_registry",
                        rulespecs.RulespecRegistry(rulespec_group_registry))

    assert "notification_parameters:xyz" not in rulespecs.rulespec_registry
    assert "xyz" not in utils.notification_parameter_registry
    cmk.gui.wato.register_notification_parameters("xyz", Dictionary(
        help="slosh",
        elements=[],
    ))

    cls = utils.notification_parameter_registry["xyz"]
    assert isinstance(cls.spec, Dictionary)
    assert cls.spec.help() == "slosh"

    assert "notification_parameters:xyz" in rulespecs.rulespec_registry
