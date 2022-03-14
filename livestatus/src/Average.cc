// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Average.h"

#include <cmath>

#include "ChronoUtils.h"

namespace {
constexpr double percentile = 0.50;
constexpr double horizon = 10;  // seconds
const double weight_per_second = pow(1.0 - percentile, 1.0 / horizon);
}  // namespace

// TODO (sk): unit tests
// Please look at check_mk_base.py:get_average for details on the averaging
// algorithm. It's the same as here.
void Average::update(double value) {
    auto now = std::chrono::steady_clock::now();
    std::scoped_lock l(_lock);
    if (_last_update == std::chrono::steady_clock::time_point{}) {
        _average = value;
    } else {
        auto timedif =
            mk::ticks<std::chrono::duration<double>>(now - _last_update);
        if (timedif == 0) {
            // Force at least half a second. Can happen e.g. for latency
            // updates
            timedif = 0.5;
        }
        double weight = pow(weight_per_second, timedif);
        _average = _average * weight + value * (1 - weight);
    }
    _last_update = now;
}
