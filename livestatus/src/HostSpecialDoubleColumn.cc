// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "HostSpecialDoubleColumn.h"

#include <chrono>

#include "Row.h"

#ifdef CMC
#include <ratio>

#include "Object.h"
#include "State.h"
#include "Timeperiod.h"
#else
#include <ctime>

#include "nagios.h"
#endif

using namespace std::chrono_literals;

double HostSpecialDoubleColumn::getValue(Row row) const {
#ifdef CMC
    if (const auto *object = columnData<Object>(row)) {
        return staleness(object);
    }
#else
    if (const auto *hst = columnData<host>(row)) {
        extern int interval_length;
        return static_cast<double>(time(nullptr) - hst->last_check) /
               ((hst->check_interval == 0 ? 1 : hst->check_interval) *
                interval_length);
    }
#endif
    return 0;
}

#ifdef CMC
// static
double HostSpecialDoubleColumn::staleness(const Object *object) {
    const auto *state = object->state();
    std::chrono::system_clock::duration check_result_age;
    const Timeperiod *check_period = object->_check_period;
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
            check_result_age = 0s;
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
           (interval == 0s ? 1 : interval.count());
}
#endif
