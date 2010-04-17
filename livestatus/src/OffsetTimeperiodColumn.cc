// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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


#include "nagios.h"
#include <stdint.h>
#include "OffsetTimeperiodColumn.h"
#include "logger.h"


OffsetTimeperiodColumn::OffsetTimeperiodColumn(string name, string description, int offset, int indirect_offset) 
    : OffsetIntColumn(name, description, offset, indirect_offset), _cache_time(0) 
{
    pthread_mutex_init(&_cache_lock, 0);
}


OffsetTimeperiodColumn::~OffsetTimeperiodColumn()
{
    pthread_mutex_destroy(&_cache_lock);
}

int32_t OffsetTimeperiodColumn::getValue(void *data, Query *)
{
    data = shiftPointer(data);
    if (!data)
	return 0;

    timeperiod *tp = *(timeperiod **)((char *)data + offset());

    if (!tp)
	return 1; // no timeperiod set -> Nagios assumes 7x24
    else if (inTimeperiod(tp))
	return 1;
    else
	return 0;
}

bool OffsetTimeperiodColumn::inTimeperiod(timeperiod *tp)
{
    pthread_mutex_lock(&_cache_lock);

    time_t now = time(0);
    if (now != _cache_time) {
	_cache.clear();
	_cache_time = now;
    }

    bool is_in;

    _cache_t::iterator it = _cache.find(tp);
    if (it != _cache.end())
	is_in = it->second;
    else {
	is_in = 0 == check_time_against_period(now, tp);
	_cache.insert(make_pair(tp, is_in));
    }
    pthread_mutex_unlock(&_cache_lock);
    return is_in;
}

