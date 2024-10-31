from polyfactory.factories import TypedDictFactory

from cmk.utils.notify_types import (
    EventRule,
    get_rules_related_to_parameter,
    NotificationParameterID,
)


class EventRuleFactory(TypedDictFactory[EventRule]): ...


def test_get_rules_related_to_parameter() -> None:
    notification_parameter_id = NotificationParameterID("<uuid-1>")
    related_rule = EventRuleFactory.build(notify_plugin=("slack", notification_parameter_id))
    event_rules = [related_rule, EventRuleFactory.build(), EventRuleFactory.build()]

    value = get_rules_related_to_parameter(event_rules, notification_parameter_id)
    expected = [related_rule]

    assert value == expected
