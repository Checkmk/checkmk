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

#include "TimeperiodsCache.h"
#include <ostream>
#include <ratio>
#include <string>
#include <utility>
#include "Logger.h"

using std::lock_guard;
using std::mutex;
using std::string;
using std::chrono::system_clock;
using std::chrono::minutes;

extern timeperiod *timeperiod_list;

TimeperiodsCache::TimeperiodsCache(Logger *logger) : _logger(logger) {}

void TimeperiodsCache::logCurrentTimeperiods() {
    lock_guard<mutex> lg(_mutex);
    // Loop over all timeperiods and compute if we are currently in. Detect the
    // case where no time periods are known (yet!). This might be the case when
    // a timed event broker message arrives *before* the start of the event
    // loop.
    auto now = system_clock::to_time_t(system_clock::now());
    for (timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        bool is_in = check_time_against_period(now, tp) == 0;
        // check previous state and log transition if state has changed
        auto it = _cache.find(tp);
        if (it == _cache.end()) {  // first entry
            logTransition(tp->name, -1, is_in ? 1 : 0);
            _cache.emplace(tp, is_in);
        }
        logTransition(tp->name, it->second ? 1 : 0, is_in ? 1 : 0);
    }
}

void TimeperiodsCache::update(system_clock::time_point now) {
    lock_guard<mutex> lg(_mutex);
    // Update cache only once a minute. The timeperiod definitions have a
    // 1-minute granularity, so a 1-second resultion is not needed.
    if (now < _last_update + minutes(1)) {
        return;
    }
    _last_update = now;

    // Loop over all timeperiods and compute if we are currently in. Detect the
    // case where no time periods are known (yet!). This might be the case when
    // a timed event broker message arrives *before* the start of the event
    // loop.
    for (timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        bool is_in =
            check_time_against_period(system_clock::to_time_t(now), tp) == 0;
        // check previous state and log transition if state has changed
        auto it = _cache.find(tp);
        if (it == _cache.end()) {  // first entry
            logTransition(tp->name, -1, is_in ? 1 : 0);
            _cache.emplace(tp, is_in);
        } else if (it->second != is_in) {
            logTransition(tp->name, it->second ? 1 : 0, is_in ? 1 : 0);
            it->second = is_in;
        }
    }
    if (timeperiod_list != nullptr) {
        Informational(_logger)
            << "Timeperiod cache not updated, there are no timeperiods (yet)";
    }
}

bool TimeperiodsCache::inTimeperiod(const string &tpname) const {
    for (timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        if (tpname == tp->name) {
            return inTimeperiod(tp);
        }
    }
    return true;  // unknown timeperiod is assumed to be 24X7
}

bool TimeperiodsCache::inTimeperiod(const timeperiod *tp) const {
    lock_guard<mutex> lg(_mutex);
    auto it = _cache.find(tp);
    if (it == _cache.end()) {
        // Problem: check_time_against_period is not thread safe, so we can't
        // use it here.
        Informational(_logger) << "No timeperiod information available for "
                               << tp->name << ". Assuming out of period.";
        return false;
    }
    return it->second;
}

void TimeperiodsCache::logTransition(char *name, int from, int to) const {
    Informational(_logger) << "TIMEPERIOD TRANSITION: " << name << ";" << from
                           << ";" << to;
}
