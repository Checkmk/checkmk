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

#ifndef TableLog_h
#define TableLog_h

// IWYU pragma: no_include <bits/shared_ptr.h>
#include "config.h"  // IWYU pragma: keep
#include <ctime>
#include <memory>  // IWYU pragma: keep
#include <string>
#include "Table.h"
#include "contact_fwd.h"
class Column;
class Logfile;
class LogCache;
class MonitoringCore;
class Query;
class Row;

class TableLog : public Table {
public:
    TableLog(MonitoringCore *mc, LogCache *log_cache);

    std::string name() const override;
    std::string namePrefix() const override;
    void answerQuery(Query *query) override;
    bool isAuthorized(Row row, contact *ctc) override;
    std::shared_ptr<Column> column(std::string colname) override;

private:
    LogCache *_log_cache;
    bool answerQuery(Query *, Logfile *, time_t, time_t);
};

#endif  // TableLog_h
