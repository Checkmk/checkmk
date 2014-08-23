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

#include "nagios.h"
#include "Query.h"
#include "OffsetStringColumn.h"
#include "OffsetTimeperiodColumn.h"
#include "TableTimeperiods.h"

extern timeperiod *timeperiod_list;

TableTimeperiods::TableTimeperiods()
{
    addColumns(this, "", -1);
}


void TableTimeperiods::addColumns(Table *table, string prefix, int indirect_offset)
{
    timeperiod tp;
    char *ref = (char *)&tp;
    table->addColumn(new OffsetStringColumn(prefix + "name",
                "The name of the timeperiod", (char *)(&tp.name) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "alias",
                "The alias of the timeperiod", (char *)(&tp.alias) - ref, indirect_offset));
    table->addColumn(new OffsetTimeperiodColumn(prefix + "in",
                "Wether we are currently in this period (0/1)", -1, indirect_offset));
    // TODO: add days and exceptions
}


void TableTimeperiods::answerQuery(Query *query)
{
    timeperiod *tp = timeperiod_list;
    while (tp) {
        if (!query->processDataset(tp)) break;
        tp = tp->next;
    }
}
