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

#ifndef TableEventConsoleEvents_h
#define TableEventConsoleEvents_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "TableEventConsole.h"
#include "contact_fwd.h"
class MonitoringCore;
class Row;
class Table;

class TableEventConsoleEvents : public TableEventConsole {
public:
    explicit TableEventConsoleEvents(MonitoringCore *mc);
    std::string name() const override;
    std::string namePrefix() const override;
    static void addColumns(Table *table, MonitoringCore *mc);
    bool isAuthorized(Row row, const contact *ctc) const override;
};

#endif  // TableEventConsoleEvents_h
