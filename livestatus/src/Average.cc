// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Average.h"
#include <cmath>

namespace {
constexpr double percentile = 0.50;
constexpr double horizon = 10;  // seconds
}  // namespace

// Please look at check_mk_base.py:get_average for details on the averaging
// algorithm. It's the same as here.
void Average::update(double value) {
    auto now = std::chrono::steady_clock::now();
    if (_last_update == std::chrono::steady_clock::time_point()) {
        _average = value;
    } else {
        double timedif =
            std::chrono::duration<double>(now - _last_update).count();
        if (timedif == 0) {
            // Force at least halve a second. Can happen e.g. for latency
            // updates
            timedif = 0.5;
        }
        double weight_per_second = pow(1.0 - percentile, 1.0 / horizon);
        double weight = pow(weight_per_second, timedif);
        _average = _average * weight + value * (1 - weight);
    }
    _last_update = now;
}
