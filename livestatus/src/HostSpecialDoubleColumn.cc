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

#include "HostSpecialDoubleColumn.h"
#include "Row.h"

#ifdef CMC
// duration_cast uses enable_if as an implementation detail, similar bug as
// https://github.com/include-what-you-use/include-what-you-use/issues/434
// IWYU pragma: no_include <type_traits>
#include <chrono>
#include <ratio>
#include "Object.h"
#include "State.h"
#include "Timeperiod.h"
#else
#include <ctime>
#include "nagios.h"
#endif

double HostSpecialDoubleColumn::getValue(Row row) const {
#ifdef CMC
    if (auto object = columnData<Object>(row)) {
        switch (_type) {
            case Type::staleness:
                return staleness(object);
        }
    }
#else
    if (auto hst = columnData<host>(row)) {
        switch (_type) {
            case Type::staleness: {
                extern int interval_length;
                return (time(nullptr) - hst->last_check) /
                       ((hst->check_interval == 0 ? 1 : hst->check_interval) *
                        interval_length);
            }
        }
    }
#endif
    return 0;
}

#ifdef CMC
// static
double HostSpecialDoubleColumn::staleness(const Object *object) {
    auto state = object->state();
    std::chrono::system_clock::duration check_result_age;
    Timeperiod *check_period = object->_check_period;
    std::chrono::system_clock::time_point last_period_change =
        check_period->lastStateChange();
    std::chrono::system_clock::time_point last_check = state->_last_check;

    // Compute the age of the check result. When the check is currently in its
    // check period then...
    auto m_now = std::chrono::system_clock::now();
    if (check_period->isActive()) {
        // Has a check happened since the beginning of the current phase? Then
        // simply compare last check with current time. This should be the 99%
        // case.
        if (last_check >= last_period_change) {
            check_result_age = m_now - last_check;

        } else {
            // otherwise the active phase has just begun. Take the time since
            // the beginning of the phase.
            check_result_age = m_now - last_period_change;

            // Add time at the end of the pre-last transition
            std::chrono::system_clock::time_point prelast_period_change =
                check_period->previousLastStateChange();
            if (prelast_period_change !=
                std::chrono::system_clock::time_point()) {
                if (last_check < prelast_period_change) {
                    check_result_age += prelast_period_change - last_check;
                }
                // else: a check happend out of the check period. Ignore this
            }
            // else: no information about past. Ignore this
        }
    } else {
        // Check is currently out of its check period? Then use the beginning of
        // the inactive phase as reference for computing the check age. This
        // effectively freezes the staleness value when a goes goes into its
        // inactive phase.
        if (last_period_change != std::chrono::system_clock::time_point()) {
            check_result_age = last_period_change - last_check;
        } else {
            // e.g. for timeperiod "never"
            check_result_age = std::chrono::seconds(0);
        }
    }

    // Is the checks' result based on cached agent data? Then use the age of
    // that data as check result age
    std::chrono::duration<double> interval;
    if (state->_cached_at != std::chrono::system_clock::time_point()) {
        // Cache interval and check interval can add up in the worst case.
        interval = state->_cache_interval + object->_check_interval;

        std::chrono::system_clock::duration cached_age =
            m_now - state->_cached_at;
        if (cached_age > check_result_age) {
            check_result_age = cached_age;
        }
    } else {
        interval = object->_check_interval;
    }

    // Check_MK configures the interval for its passive checks correctly. Just
    // make sure that we do not fail if it is set to 0 by some error.
    return std::chrono::duration_cast<std::chrono::seconds>(check_result_age)
               .count() /
           (interval == std::chrono::seconds(0) ? 1 : interval.count());
}
#endif
