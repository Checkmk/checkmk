// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#include "CustomTimeperiodColumn.h"
#include "TimeperiodsCache.h"

extern TimeperiodsCache *g_timeperiods_cache;

// Get the name of a timeperiod from a custom variable and
// lookup the current state of that period
int32_t CustomTimeperiodColumn::getValue(void *data, Query *)
{
    customvariablesmember *cvm = getCVM(data);
    while (cvm) {
        if (cvm->variable_name == _varname)
            return g_timeperiods_cache->inTimeperiod(cvm->variable_value);
        cvm = cvm->next;
    }
    return 1; // assume 7X24
}

customvariablesmember *CustomTimeperiodColumn::getCVM(void *data)
{
    if (!data) return 0;
    data = shiftPointer(data);
    if (!data) return 0;
    return *(customvariablesmember **)((char *)data + _offset);
}

