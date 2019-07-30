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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "global_counters.h"
#include <ctime>
#include <vector>

namespace {
constexpr int num_counters = 10;

struct CounterInfo {
    double value;
    double last_value;
    double rate;
};

std::vector<CounterInfo> counters(num_counters);

CounterInfo &counter(Counter which) {
    return counters[static_cast<int>(which)];
}

time_t last_statistics_update = 0;
constexpr time_t statistics_interval = 5;
constexpr double rating_weight = 0.25;

double lerp(double a, double b, double t) { return (1 - t) * a + t * b; }
}  // namespace

void counterIncrement(Counter which) { counter(which).value++; }

const double *counterAddress(Counter which) { return &counter(which).value; }

const double *counterRateAddress(Counter which) { return &counter(which).rate; }

void do_statistics() {
    time_t now = time(nullptr);
    if (last_statistics_update == 0) {
        last_statistics_update = now;
        return;
    }
    time_t delta_time = now - last_statistics_update;
    if (delta_time < statistics_interval) {
        return;
    }
    last_statistics_update = now;
    for (auto &c : counters) {
        double old_rate = c.rate;
        double new_rate = (c.value - c.last_value) / delta_time;
        c.rate = lerp(old_rate, new_rate, old_rate == 0 ? 1 : rating_weight);
        c.last_value = c.value;
    }
}
