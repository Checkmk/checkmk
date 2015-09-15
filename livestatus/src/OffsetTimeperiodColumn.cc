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

