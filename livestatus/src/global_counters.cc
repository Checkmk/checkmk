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

uint64_t g_counters[NUM_COUNTERS];
uint64_t g_last_counter[NUM_COUNTERS];
double g_counter_rate[NUM_COUNTERS];

time_t last_statistics_update = 0;
#define STATISTICS_INTERVAL 5
#define RATING_WEIGHT 0.25

void do_statistics() {
    if (last_statistics_update == 0) {
        last_statistics_update = time(nullptr);
        for (unsigned i = 0; i < NUM_COUNTERS; i++) {
            g_counters[i] = 0;
            g_last_counter[i] = 0;
            g_counter_rate[i] = 0.0;
        }
        return;
    }
    time_t now = time(nullptr);
    time_t delta_time = now - last_statistics_update;
    if (delta_time >= STATISTICS_INTERVAL) {
        last_statistics_update = now;
        for (unsigned i = 0; i < NUM_COUNTERS; i++) {
            auto delta_value = g_counters[i] - g_last_counter[i];
            double new_rate = static_cast<double>(delta_value) /
                              static_cast<double>(delta_time);
            double old_rate = g_counter_rate[i];
            double avg_rate;
            if (old_rate == 0) {
                avg_rate = new_rate;
            } else {
                avg_rate =
                    old_rate * (1.0 - RATING_WEIGHT) + new_rate * RATING_WEIGHT;
            }
            g_counter_rate[i] = avg_rate;
            g_last_counter[i] = g_counters[i];
        }
    }
}
