#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, Union

HostCommand = Literal[
    'ACKNOWLEDGE_HOST_PROBLEM',
    'REMOVE_HOST_ACKNOWLEDGEMENT',
    'ADD_HOST_COMMENT',
    'DEL_HOST_COMMENT',
    'SCHEDULE_HOST_DOWNTIME',
    'MODIFY_HOST_DOWNTIME',
    'DEL_HOST_DOWNTIME',
    'START_EXECUTING_HOST_CHECKS',
    'STOP_EXECUTING_HOST_CHECKS',
    'ENABLE_HOST_CHECK',
    'DISABLE_HOST_CHECK',
    'ENABLE_PASSIVE_HOST_CHECKS',
    'DISABLE_PASSIVE_HOST_CHECKS',
    'ENABLE_HOST_NOTIFICATIONS',
    'DISABLE_HOST_NOTIFICATIONS',
    'ENABLE_HOST_SVC_NOTIFICATIONS',
    'DISABLE_HOST_SVC_NOTIFICATIONS',
    'SCHEDULE_FORCED_HOST_CHECK',
    'PROCESS_HOST_CHECK_RESULT',
    'SEND_CUSTOM_HOST_NOTIFICATION',
    'CHANGE_HOST_MODATTR',
]  # yapf: disable

ServiceCommand = Literal[
    'ACKNOWLEDGE_SVC_PROBLEM',
    'REMOVE_SVC_ACKNOWLEDGEMENT',
    'ADD_SVC_COMMENT',
    'DEL_SVC_COMMENT',
    'SCHEDULE_SVC_DOWNTIME',
    'MODIFY_SVC_DOWNTIME',
    'DEL_SVC_DOWNTIME',
    'START_EXECUTING_SVC_CHECKS',
    'STOP_EXECUTING_SVC_CHECKS',
    'ENABLE_SVC_CHECK',
    'DISABLE_SVC_CHECK',
    'ENABLE_PASSIVE_SVC_CHECKS',
    'DISABLE_PASSIVE_SVC_CHECKS',
    'ENABLE_SVC_NOTIFICATIONS',
    'DISABLE_SVC_NOTIFICATIONS',
    'SCHEDULE_FORCED_SVC_CHECK',
    'PROCESS_SERVICE_CHECK_RESULT',
    'SEND_CUSTOM_SVC_NOTIFICATION',
    'CHANGE_SVC_MODATTR',
]  # yapf: disable

OtherCommand = Literal[
    'ENABLE_NOTIFICATIONS',
    'DISABLE_NOTIFICATIONS',
    'ENABLE_FLAP_DETECTION',
    'DISABLE_FLAP_DETECTION',
    'ENABLE_PERFORMANCE_DATA',
    'DISABLE_PERFORMANCE_DATA',
    'ENABLE_EVENT_HANDLERS',
    'DISABLE_EVENT_HANDLERS',
    'SAVE_STATE_INFORMATION',
]  # yapf: disable

EnterpriseHostCommand = Literal[
    'PROCESS_HOST_PERFDATA',
    'UPDATE_SHADOW_HOST_STATE',
]  # yapf: disable

EnterpriseServiceCommand = Literal[
    'PROCESS_SVC_PERFDATA',
    'UPDATE_SHADOW_SERVICE_STATE',
]  # yapf: disable

EnterpriseOtherCommand = Literal[
    'LOG',
    'MK_LOGWATCH_ACKNOWLEDGE',
    'RELOAD_CONFIG',
    'REOPEN_DAEMONLOG',
    'ROTATE_LOGFILE',
    'SEGFAULT',
]  # yapf: disable

LivestatusCommand = Union[HostCommand, ServiceCommand, OtherCommand, EnterpriseHostCommand,
                          EnterpriseServiceCommand, EnterpriseOtherCommand]
