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

#include "TableTimeperiods.h"
#include <memory>
#include "Column.h"
#include "OffsetStringColumn.h"
#include "Query.h"
#include "Row.h"
#include "TimeperiodColumn.h"
#include "nagios.h"

extern timeperiod *timeperiod_list;

TableTimeperiods::TableTimeperiods(MonitoringCore *mc) : Table(mc) {
    addColumn(std::make_unique<OffsetStringColumn>(
        "name", "The name of the timeperiod", -1, -1, -1,
        DANGEROUS_OFFSETOF(timeperiod, name)));
    addColumn(std::make_unique<OffsetStringColumn>(
        "alias", "The alias of the timeperiod", -1, -1, -1,
        DANGEROUS_OFFSETOF(timeperiod, alias)));
    addColumn(std::make_unique<TimeperiodColumn>(
        "in", "Wether we are currently in this period (0/1)", -1, -1, -1, 0));
    // TODO(mk): add days and exceptions
}

std::string TableTimeperiods::name() const { return "timeperiods"; }

std::string TableTimeperiods::namePrefix() const { return "timeperiod_"; }

void TableTimeperiods::answerQuery(Query *query) {
    for (timeperiod *tp = timeperiod_list; tp != nullptr; tp = tp->next) {
        if (!query->processDataset(Row(tp))) {
            break;
        }
    }
}
