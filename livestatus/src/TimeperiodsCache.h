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

#ifndef _TimeperiodsCache_h
#define _TimeperiodsCache_h

#include <map>
#include "nagios.h"

class TimeperiodsCache
{
    time_t _cache_time;
    typedef std::map<timeperiod *, bool> _cache_t;
    _cache_t _cache;
    pthread_mutex_t _cache_lock;

public:
    TimeperiodsCache();
    ~TimeperiodsCache();
    void update(time_t now);
    bool inTimeperiod(timeperiod *tp);
    bool inTimeperiod(const char *tpname);
    void logCurrentTimeperiods();
private:
    void logTransition(char *name, int from, int to);
};

#endif // _TimeperiodsCache_h
