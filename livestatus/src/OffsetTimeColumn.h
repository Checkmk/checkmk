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

