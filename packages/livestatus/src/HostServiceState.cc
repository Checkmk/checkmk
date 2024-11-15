// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/HostServiceState.h"

#include "livestatus/ChronoUtils.h"

using namespace std::chrono_literals;

void HostServiceState::computePerStateDurations(
    std::chrono::system_clock::duration query_timeframe) {
    // TODO(sp): _duration is already set, but we should probably do it here,
    // but the code at the call sites is quite confusing: It's probably just
    // (_until - _from), but who knows? Furthermore, there seems to be some
    // confusion regarding the query_timeframe: Is the interval from which it is
    // computed closed or half-open? Should there be a -1s somewhere? The two
    // statehist implementations do not agree on this. :-/
    _duration_part = mk::ticks<std::chrono::duration<double>>(_duration) /
                     mk::ticks<std::chrono::duration<double>>(query_timeframe);

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
        default:
            // TODO(sp) Should we really ignore invalid log entries?
            break;
    }
}
