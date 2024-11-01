import pytest

from cmk.gui.watolib.configuration_entity import configuration_entity as ce
from cmk.gui.watolib.configuration_entity.type_defs import ConfigEntityType


@pytest.mark.parametrize(
    "specifier, expected",
    [
        ("asciimail", "ASCII Email"),
        ("cisco_webex_teams", "Cisco Webex Teams"),
        ("ilert", "iLert"),
        ("jira_issues", "JIRA (Commercial editions only)"),
        ("mail", "HTML Email"),
        ("mkeventd", "Forward Notification to Event Console"),
        ("msteams", "Microsoft Teams"),
        ("opsgenie_issues", "Opsgenie"),
        ("pagerduty", "PagerDuty"),
        ("pushover", "Push Notifications (using Pushover)"),
        ("servicenow", "Servicenow (Enterprise only)"),
        ("signl4", "SIGNL4 Alerting"),
        ("slack", "Slack or Mattermost"),
        ("sms", "SMS (using smstools)"),
        ("sms_api", "SMS (using modem API)"),
        ("spectrum", "Spectrum Server"),
        ("victorops", "Splunk On-Call"),
        pytest.param("unknown", "unknown", id="Fallback to specifier when not found."),
    ],
)
def test_get_readable_entity_selection__notification_parameter(
    specifier: str, expected: str
) -> None:
    value = ce.get_readable_entity_selection(
        entity_type=ConfigEntityType.notification_parameter,
        entity_type_specifier=specifier,
    )
    assert value == expected
