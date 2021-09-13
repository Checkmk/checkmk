// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostServiceState.h"

using namespace std::chrono_literals;

HostServiceState::HostServiceState()
    : _is_host{false}
    , _lineno{0}
    , _duration{0s}
    , _duration_part{0}
    , _duration_unmonitored{0s}
    , _duration_part_unmonitored{0}
    , _duration_ok{0s}
    , _duration_part_ok{0}
    , _duration_warning{0s}
    , _duration_part_warning{0}
    , _duration_critical{0s}
    , _duration_part_critical{0}
    , _duration_unknown{0s}
    , _duration_part_unknown{0}
    , _host_down{0}
    , _state{0}
    , _in_notification_period{0}
    , _in_service_period{0}
    , _in_downtime{0}
    , _in_host_downtime{0}
    , _is_flapping{0}
    , _may_no_longer_exist{false}
    , _has_vanished{false}
    , _host{nullptr}
    , _service{nullptr} {}

#ifdef CMC
void HostServiceState::computePerStateDurations() {
    _duration_unmonitored = 0s;
    _duration_part_unmonitored = 0;
    _duration_ok = 0s;
    _duration_part_ok = 0;
    _duration_warning = 0s;
    _duration_part_warning = 0;
    _duration_critical = 0s;
    _duration_part_critical = 0;
    _duration_unknown = 0s;
    _duration_part_unknown = 0;

    switch (_state) {
        case -1:
            _duration_unmonitored = _duration;
            _duration_part_unmonitored = _duration_part;
            break;
        case 0:
            _duration_ok = _duration;
            _duration_part_ok = _duration_part;
            break;
        case 1:
            _duration_warning = _duration;
            _duration_part_warning = _duration_part;
            break;
        case 2:
            _duration_critical = _duration;
            _duration_part_critical = _duration_part;
            break;
        case 3:
            _duration_unknown = _duration;
            _duration_part_unknown = _duration_part;
            break;
    }
}
#endif
