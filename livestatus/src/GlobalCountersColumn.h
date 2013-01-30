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

#ifndef GlobalCountersColumn_h
#define GlobalCountersColumn_h

#include "config.h"

#include "Column.h"
#include "global_counters.h"

class GlobalCountersColumn : public Column
{
    unsigned _counter_index;
    bool _do_average;

public:
    GlobalCountersColumn(string name, string description, unsigned counter_index, bool do_average)
        : Column(name, description, -1), _counter_index(counter_index), _do_average(do_average) {}
    int type() { return _do_average ? COLTYPE_DOUBLE : COLTYPE_INT; }
    void output(void *, Query *);
    Filter *createFilter(int operator_id __attribute__ ((__unused__)), char *value __attribute__ ((__unused__))) { return 0; }
};


#endif // GlobalCountersColumn_h

