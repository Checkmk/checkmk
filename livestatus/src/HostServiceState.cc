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
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

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
