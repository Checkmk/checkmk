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

#include "OringFilter.h"


bool OringFilter::accepts(void *data)
{
    for (_subfilters_t::iterator it = _subfilters.begin();
            it != _subfilters.end();
            ++it)
    {
        Filter *filter = *it;
        if (filter->accepts(data))
            return true;
    }
    return false;
}

bool OringFilter::optimizeBitmask(const char *columnname, uint32_t *mask)
{
    // We can only optimize, if *all* subfilters are filters for the
    // same column.
    uint32_t m = 0;

    for (_subfilters_t::iterator it = _subfilters.begin();
            it != _subfilters.end();
            ++it)
    {
        Filter *filter = *it;
        uint32_t mm = 0xffffffff;
        if (!filter->optimizeBitmask(columnname, &mm))
            return false; // wrong column
        m |= mm;
    }
    *mask &= m;
    return true;
}

