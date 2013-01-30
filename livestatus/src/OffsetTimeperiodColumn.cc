// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
#include "TimeperiodsCache.h"

extern TimeperiodsCache *g_timeperiods_cache;


    OffsetTimeperiodColumn::OffsetTimeperiodColumn(string name, string description, int offset, int indirect_offset)
: OffsetIntColumn(name, description, offset, indirect_offset)
{
}


int32_t OffsetTimeperiodColumn::getValue(void *data, Query *)
{
    data = shiftPointer(data);
    if (!data)
        return 0;

    timeperiod *tp;
    if (offset() == -1)
        tp = (timeperiod *)data;
    else
        tp = *(timeperiod **)((char *)data + offset());


    if (!tp)
        return 1; // no timeperiod set -> Nagios assumes 7x24
    else if (g_timeperiods_cache->inTimeperiod(tp))
        return 1;
    else
        return 0;
}

