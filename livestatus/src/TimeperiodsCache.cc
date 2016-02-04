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

#include "TimeperiodsCache.h"
#include <stdio.h>
#include <string.h>
#include <syslog.h>
#include <time.h>
#include <utility>
#include "logger.h"

using std::make_pair;
using mk::lock_guard;
using mk::mutex;

extern timeperiod *timeperiod_list;

TimeperiodsCache::TimeperiodsCache() { _cache_time = 0; }

TimeperiodsCache::~TimeperiodsCache() = default;

void TimeperiodsCache::logCurrentTimeperiods() {
    lock_guard<mutex> lg(_cache_lock);
    time_t now = time(nullptr);
    // Loop over all timeperiods and compute if we are
    // currently in. Detect the case where no time periods
    // are known (yet!). This might be the case when a timed
    // event broker message arrives *before* the start of the
    // event loop.
    timeperiod *tp = timeperiod_list;
    while (tp != nullptr) {
        bool is_in = 0 == check_time_against_period(now, tp);
        // check previous state and log transition if state has changed
        auto it = _cache.find(tp);
        if (it == _cache.end()) {  // first entry
            logTransition(tp->name, -1, is_in ? 1 : 0);
            _cache.insert(make_pair(tp, is_in));
        }
        logTransition(tp->name, it->second ? 1 : 0, is_in ? 1 : 0);
        tp = tp->next;
    }
}

void TimeperiodsCache::update(time_t now) {
    lock_guard<mutex> lg(_cache_lock);

    // update cache only once a minute. The timeperiod
    // definitions have 1 minute as granularity, so a
    // 1sec resultion is not needed.
    int minutes = now / 60;
    if (minutes == _cache_time) {
        return;
    }

    // Loop over all timeperiods and compute if we are
    // currently in. Detect the case where no time periods
    // are known (yet!). This might be the case when a timed
    // event broker message arrives *before* the start of the
    // event loop.
    timeperiod *tp = timeperiod_list;
    int num_periods = 0;
    while (tp != nullptr) {
        bool is_in = 0 == check_time_against_period(now, tp);

        // check previous state and log transition if state has changed
        auto it = _cache.find(tp);
        if (it == _cache.end()) {  // first entry
            logTransition(tp->name, -1, is_in ? 1 : 0);
            _cache.insert(make_pair(tp, is_in));
        } else if (it->second != is_in) {
            logTransition(tp->name, it->second ? 1 : 0, is_in ? 1 : 0);
            it->second = is_in;
        }

        tp = tp->next;
        num_periods++;
    }
    if (num_periods > 0) {
        _cache_time = minutes;
    } else {
        logger(LG_INFO,
               "Timeperiod cache not updated, there are no timeperiods (yet)");
    }
}

bool TimeperiodsCache::inTimeperiod(const char *tpname) {
    timeperiod *tp = timeperiod_list;
    while (tp != nullptr) {
        if (strcmp(tpname, tp->name) == 0) {
            return inTimeperiod(tp);
        }
        tp = tp->next;
    }
    return true;  // unknown timeperiod is assumed to be 7X24
}

bool TimeperiodsCache::inTimeperiod(timeperiod *tp) {
    lock_guard<mutex> lg(_cache_lock);
    auto it = _cache.find(tp);
    bool is_in;
    if (it != _cache.end()) {
        is_in = it->second;
    } else {
        logger(LG_INFO,
               "No timeperiod information available for %s. Assuming out of "
               "period.",
               tp->name);
        is_in = false;
        // Problem: The method check_time_against_period is to a high
        // degree not thread safe. In the current situation Icinga is
        // very probable to hang up forever.
        // time_t now = time(0);
        // is_in = 0 == check_time_against_period(now, tp);
    }
    return is_in;
}

void TimeperiodsCache::logTransition(char *name, int from, int to) {
    char buffer[256];
    snprintf(buffer, sizeof(buffer), "TIMEPERIOD TRANSITION: %s;%d;%d", name,
             from, to);
    write_to_all_logs(buffer, LOG_INFO);
}
