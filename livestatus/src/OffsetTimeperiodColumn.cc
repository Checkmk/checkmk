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

#include "OffsetTimeperiodColumn.h"
#include "TimeperiodsCache.h"
#include "nagios.h"

using std::string;

extern TimeperiodsCache *g_timeperiods_cache;

OffsetTimeperiodColumn::OffsetTimeperiodColumn(string name, string description,
                                               int offset, int indirect_offset,
                                               int extra_offset)
    : OffsetIntColumn(name, description, offset, indirect_offset,
                      extra_offset) {}

int32_t OffsetTimeperiodColumn::getValue(void *data, Query * /*unused*/) {
    data = shiftPointer(data);
    if (data == nullptr) {
        return 0;
    }

    timeperiod *tp;
    if (offset() == -1) {
        tp = reinterpret_cast<timeperiod *>(data);
    } else {
        tp = *reinterpret_cast<timeperiod **>(reinterpret_cast<char *>(data) +
                                              offset());
    }

    if (tp == nullptr) {
        return 1;  // no timeperiod set -> Nagios assumes 7x24
    }
    if (g_timeperiods_cache->inTimeperiod(tp)) {
        return 1;
    }
    return 0;
}
