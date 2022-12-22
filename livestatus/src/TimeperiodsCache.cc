// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TimeperiodsCache.h"

#include <utility>

#include "Logger.h"
#include "nagios.h"

using namespace std::chrono_literals;

TimeperiodsCache::TimeperiodsCache(Logger *logger) : _logger(logger) {}

void TimeperiodsCache::logCurrentTimeperiods() {
    std::lock_guard<std::mutex> lg(_mutex);
    // Loop over all timeperiods and compute if we are currently in. Detect the
    // case where no time periods are known (yet!). This might be the case when
    // a timed event broker message arrives *before* the start of the event
    // loop.
    auto now =
        std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
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

void TimeperiodsCache::update(std::chrono::system_clock::time_point now) {
    std::lock_guard<std::mutex> lg(_mutex);
    // Update cache only once a minute. The timeperiod definitions have a
    // 1-minute granularity, so a 1-second resultion is not needed.
    if (now < _last_update + 1min) {
        return;
    }
    _last_update = now;

    // Loop over all timeperiods and compute if we are currently in. Detect the
    // case where no time periods are known (yet!). This might be the case when
    // a timed event broker message arrives *before* the start of the event
    // loop.
    for (timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        bool is_in = check_time_against_period(
                         std::chrono::system_clock::to_time_t(now), tp) == 0;
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

bool TimeperiodsCache::inTimeperiod(const std::string &tpname) const {
    for (timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        if (tpname == tp->name) {
            return inTimeperiod(tp);
        }
    }
    return true;  // unknown timeperiod is assumed to be 24X7
}

bool TimeperiodsCache::inTimeperiod(const timeperiod *tp) const {
    std::lock_guard<std::mutex> lg(_mutex);
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
