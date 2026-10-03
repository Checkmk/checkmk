#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The notification automations.

The notification engine itself is cmk.base.notify; these only run it on request
against the configuration the automation engine keeps.
"""

import json
import logging
from pathlib import Path

import cmk.livestatus_client as livestatus
import cmk.utils.timeperiod
from cmk.automations.internal import Automation, AutomationID
from cmk.automations.results import (
    NotificationAnalyseResult,
    NotificationGetBulksResult,
    NotificationReplayResult,
    NotificationTestResult,
)
from cmk.base.automations.automations import BaseConfigState, CommonState
from cmk.base.notify import (
    find_bulks,
    make_ensure_nagios,
    make_notification_config,
    notification_analyse_backlog,
    notification_bulkdir,
    notification_replay_backlog,
    notification_test,
)
from cmk.utils import http_proxy_config
from cmk.utils.timeperiod import get_all_timeperiods


def _automation_notification_replay(
    state: CommonState,
    args: list[str],
) -> NotificationReplayResult:
    loading_result = state.loading_result
    logger = logging.getLogger("cmk.base.automations")  # this might go nowhere.

    nr = args[0]
    notification_replay_backlog(
        http_proxy_config.make_http_proxy_getter(loading_result.loaded_config.http_proxies),
        make_ensure_nagios(loading_result.loaded_config.monitoring_core),
        int(nr),
        notification_config=make_notification_config(
            state.app.edition,
            loading_result.loaded_config,
            loading_result.config_cache.ruleset_matcher,
            loading_result.config_cache.label_manager,
        ),
        define_servicegroups=loading_result.loaded_config.define_servicegroups,
        config_contacts=loading_result.loaded_config.contacts,
        all_timeperiods=get_all_timeperiods(loading_result.loaded_config.timeperiods),
        timeperiods_active=cmk.utils.timeperiod.TimeperiodActiveCoreLookup(
            livestatus.get_optional_timeperiods_active_map, log=logger.warning
        ),
    )
    return NotificationReplayResult()


def _automation_notification_analyse(
    state: CommonState,
    args: list[str],
) -> NotificationAnalyseResult:
    loading_result = state.loading_result
    logger = logging.getLogger("cmk.base.automations")  # this might go nowhere.

    nr = args[0]
    return NotificationAnalyseResult(
        notification_analyse_backlog(
            http_proxy_config.make_http_proxy_getter(loading_result.loaded_config.http_proxies),
            make_ensure_nagios(loading_result.loaded_config.monitoring_core),
            int(nr),
            notification_config=make_notification_config(
                state.app.edition,
                loading_result.loaded_config,
                loading_result.config_cache.ruleset_matcher,
                loading_result.config_cache.label_manager,
            ),
            define_servicegroups=loading_result.loaded_config.define_servicegroups,
            config_contacts=loading_result.loaded_config.contacts,
            all_timeperiods=get_all_timeperiods(loading_result.loaded_config.timeperiods),
            timeperiods_active=cmk.utils.timeperiod.TimeperiodActiveCoreLookup(
                livestatus.get_optional_timeperiods_active_map, log=logger.warning
            ),
        )
    )


def _automation_notification_test(
    state: CommonState,
    args: list[str],
) -> NotificationTestResult:
    context = json.loads(args[0])
    dispatch = args[1]

    loading_result = state.loading_result
    ensure_nagios = make_ensure_nagios(loading_result.loaded_config.monitoring_core)
    logger = logging.getLogger("cmk.base.automations")  # this might go nowhere.

    return NotificationTestResult(
        notification_test(
            context,
            http_proxy_config.make_http_proxy_getter(loading_result.loaded_config.http_proxies),
            ensure_nagios,
            notification_config=make_notification_config(
                state.app.edition,
                loading_result.loaded_config,
                loading_result.config_cache.ruleset_matcher,
                loading_result.config_cache.label_manager,
            ),
            define_servicegroups=loading_result.loaded_config.define_servicegroups,
            config_contacts=loading_result.loaded_config.contacts,
            all_timeperiods=get_all_timeperiods(loading_result.loaded_config.timeperiods),
            dispatch=dispatch,
            timeperiods_active=cmk.utils.timeperiod.TimeperiodActiveCoreLookup(
                livestatus.get_optional_timeperiods_active_map, log=logger.warning
            ),
        )
    )


def _automation_get_bulks(
    state: BaseConfigState,
    args: list[str],
) -> NotificationGetBulksResult:
    only_ripe = args[0] == "1"
    logger = logging.getLogger("cmk.base.automations")  # this might go nowhere.
    return NotificationGetBulksResult(
        find_bulks(
            only_ripe,
            bulk_root=Path(notification_bulkdir),
            bulk_interval=state.loaded_config.notification_bulk_interval,
            timeperiods_active=cmk.utils.timeperiod.TimeperiodActiveCoreLookup(
                livestatus.get_optional_timeperiods_active_map, log=logger.warning
            ),
        )
    )


automation_notification_replay = Automation(
    name=AutomationID("notification-replay"),
    state_factory=CommonState,
    handler=_automation_notification_replay,
    result=NotificationReplayResult,
)
automation_notification_analyse = Automation(
    name=AutomationID("notification-analyse"),
    state_factory=CommonState,
    handler=_automation_notification_analyse,
    result=NotificationAnalyseResult,
)
automation_notification_test = Automation(
    name=AutomationID("notification-test"),
    state_factory=CommonState,
    handler=_automation_notification_test,
    result=NotificationTestResult,
)
automation_notification_get_bulks = Automation(
    name=AutomationID("notification-get-bulks"),
    state_factory=BaseConfigState,
    handler=_automation_get_bulks,
    result=NotificationGetBulksResult,
)
