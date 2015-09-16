// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#include <stdlib.h>
#include "HostServiceState.h"

HostServiceState::~HostServiceState()
{
    if (_log_output != 0)
        free(_log_output);
}

void HostServiceState::computePerStateDurations()
{
    _duration_state_UNMONITORED = 0;
    _duration_part_UNMONITORED = 0;
    _duration_state_OK = 0;
    _duration_part_OK = 0;
    _duration_state_WARNING = 0;
    _duration_part_WARNING = 0;
    _duration_state_CRITICAL = 0;
    _duration_part_CRITICAL = 0;
    _duration_state_UNKNOWN = 0;
    _duration_part_UNKNOWN = 0;

    switch (_state) {
        case -1:
            _duration_state_UNMONITORED = _duration;
            _duration_part_UNMONITORED = _duration_part;
            break;
        case 0:
            _duration_state_OK = _duration;
            _duration_part_OK = _duration_part;
            break;
        case 1:
            _duration_state_WARNING = _duration;
            _duration_part_WARNING = _duration_part;
            break;
        case 2:
            _duration_state_CRITICAL = _duration;
            _duration_part_CRITICAL = _duration_part;
            break;
        case 3:
            _duration_state_UNKNOWN = _duration;
            _duration_part_UNKNOWN = _duration_part;
            break;
    }
}
