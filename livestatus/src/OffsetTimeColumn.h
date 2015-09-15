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

#ifndef OffsetTimeColumn_h
#define OffsetTimeColumn_h

#include "config.h"

#include <stdlib.h>
#include "OffsetIntColumn.h"


/* We are using IntColumn in order to implement a column
   of type time. This does almost the same as the time column,
   but applies a timezone offset stored in the Query. */

class OffsetTimeColumn : public OffsetIntColumn
{
public:
    OffsetTimeColumn(string name, string description, int offset, int indirect_offset = -1)
        : OffsetIntColumn(name, description, offset, indirect_offset) {}
    int type() { return COLTYPE_TIME; }
    void output(void *data, Query *query);
    Filter *createFilter(int operator_id, char *value);
};


#endif // OffsetTimeColumn_h

