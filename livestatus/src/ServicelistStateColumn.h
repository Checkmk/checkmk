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

#ifndef ServicelistStateColumn_h
#define ServicelistStateColumn_h

#include "config.h"

#include "IntColumn.h"
#include "nagios.h"

#define SLSC_NUM_OK             0
#define SLSC_NUM_WARN           1
#define SLSC_NUM_CRIT           2
#define SLSC_NUM_UNKNOWN        3
#define SLSC_NUM_PENDING        4
#define SLSC_WORST_STATE       -2

#define SLSC_NUM_HARD_OK       ( 0 + 64)
#define SLSC_NUM_HARD_WARN     ( 1 + 64)
#define SLSC_NUM_HARD_CRIT     ( 2 + 64)
#define SLSC_NUM_HARD_UNKNOWN  ( 3 + 64)
#define SLSC_WORST_HARD_STATE  (-2 + 64)

#define SLSC_NUM               -1


class ServicelistStateColumn : public IntColumn
{
    int _offset;
    int _logictype;

public:
    ServicelistStateColumn(string name, string description, int logictype, int offset, int indirect_offset)
        : IntColumn(name, description, indirect_offset), _offset(offset), _logictype(logictype) {}
    int32_t getValue(void *data, Query *);
    servicesmember *getMembers(void *data);
    static int32_t getValue(int logictype, servicesmember *services, Query *);
    static bool svcStateIsWorse(int32_t state1, int32_t state2);
};


#endif // ServicelistStateColumn_h

