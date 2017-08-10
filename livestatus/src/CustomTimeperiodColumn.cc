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

#include "CustomTimeperiodColumn.h"
#include "Column.h"
#include "Row.h"
#include "TimeperiodsCache.h"

extern TimeperiodsCache *g_timeperiods_cache;

// Get the name of a timeperiod from a custom variable and lookup the current
// state of that period
int32_t CustomTimeperiodColumn::getValue(Row row,
                                         contact * /* auth_user */) const {
    for (customvariablesmember *cvm = getCVM(row); cvm != nullptr;
         cvm = cvm->next) {
        if (cvm->variable_name == _varname) {
            return static_cast<int32_t>(
                g_timeperiods_cache->inTimeperiod(cvm->variable_value));
        }
    }
    return 1;  // assume 7X24
}

customvariablesmember *CustomTimeperiodColumn::getCVM(Row row) const {
    if (auto p = columnData<void>(row)) {
        return *offset_cast<customvariablesmember *>(p, _offset);
    }
    return nullptr;
}
