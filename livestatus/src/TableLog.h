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

#ifndef TableLog_h
#define TableLog_h

#include "config.h"  // IWYU pragma: keep
#include <time.h>
#include <string>
#include "Table.h"
#include "nagios.h"  // IWYU pragma: keep
class Column;
class Logfile;
class LogCache;
class Query;

class TableLog : public Table {
public:
    explicit TableLog(LogCache *log_cache);
    const char *name() override { return "log"; }
    const char *prefixname() override { return "logs"; }
    bool isAuthorized(contact *ctc, void *data) override;
    void handleNewMessage(Logfile *logfile, time_t since, time_t until,
                          unsigned logclasses);
    static void addColumns(Table *, std::string prefix, int indirect_offset,
                           bool add_host = true, bool add_services = true);
    void answerQuery(Query *query) override;
    Column *column(const char *colname) override;

private:
    LogCache *_log_cache;
    bool answerQuery(Query *, Logfile *, time_t, time_t);
};

#endif  // TableLog_h
