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

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include "config.h"  // IWYU pragma: keep
#include <map>
#include <memory>
#include <string>
#include "LogCache.h"
#include "Logfile.h"
#include "Table.h"
#ifdef CMC
#include "cmc.h"
#else
#include "contact_fwd.h"
#endif
class Column;
class HostServiceState;
class LogEntry;
class MonitoringCore;
class Query;
class Row;

class TableStateHistory : public Table {
public:
    TableStateHistory(MonitoringCore *mc, LogCache *log_cache);

    std::string name() const override;
    std::string namePrefix() const override;
    void answerQuery(Query *query) override;
    bool isAuthorized(Row row, const contact *ctc) const override;
    std::shared_ptr<Column> column(std::string colname) const override;

protected:
    bool _abort_query;

private:
    LogCache *_log_cache;

    int _query_timeframe;
    const Query *_query;
    int _since;
    int _until;

    // Notification periods information, name: active(1)/inactive(0)
    std::map<std::string, int> _notification_periods;

    // Helper functions to traverse through logfiles
    logfiles_t::iterator _it_logs;
    logfile_entries_t *_entries;
    logfile_entries_t::iterator _it_entries;

    void getPreviousLogentry();
    LogEntry *getNextLogentry();
    void process(Query *query, HostServiceState *hs_state);
    int updateHostServiceState(Query *query, const LogEntry *entry,
                               HostServiceState *hs_state,
                               const bool only_update);
};

#endif  // TableStateHistory_h
