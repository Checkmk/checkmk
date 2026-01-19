// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TimeperiodsCache_h
#define TimeperiodsCache_h

#include <chrono>
#include <map>
#include <mutex>
#include <string>

#include "neb/nagios.h"
class Logger;

class TimeperiodsCache {
public:
    explicit TimeperiodsCache(Logger *logger);
    void update(std::chrono::system_clock::time_point now);
    bool inTimeperiod(const timeperiod *tp) const;
    bool inTimeperiod(const std::string &tpname) const;
    void logCurrentTimeperiods();

private:
    Logger *const _logger;

    // The mutex protects _last_update and _cache.
    mutable std::mutex _mutex;
    std::chrono::system_clock::time_point _last_update;
    std::map<const timeperiod *, bool> _cache;
};

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern TimeperiodsCache *g_timeperiods_cache;

#endif  // TimeperiodsCache_h
