// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include "config.h"  // IWYU pragma: keep

#include <map>
#include <memory>
#include <string>

#include "LogCache.h"
#include "Logfile.h"
#include "Table.h"
class Column;
class Filter;
class HostServiceState;
class LogEntry;
class MonitoringCore;
class Query;
class Row;

#ifdef CMC
#include "cmc.h"
#else
#include "contact_fwd.h"
#endif

class TableStateHistory : public Table {
public:
    TableStateHistory(MonitoringCore *mc, LogCache *log_cache);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query) override;
    bool isAuthorized(Row row, const contact *ctc) const override;
    [[nodiscard]] std::shared_ptr<Column> column(
        std::string colname) const override;
    static std::unique_ptr<Filter> createPartialFilter(const Query &query);

protected:
    bool _abort_query;

private:
    LogCache *_log_cache;

    int _query_timeframe;
    int _since;
    int _until;

    // Notification periods information, name: active(1)/inactive(0)
    std::map<std::string, int> _notification_periods;

    // Helper functions to traverse through logfiles
    logfiles_t::const_iterator _it_logs;
    const logfile_entries_t *_entries;
    logfile_entries_t::const_iterator _it_entries;

    void getPreviousLogentry();
    LogEntry *getNextLogentry();
    void process(Query *query, HostServiceState *hs_state);
    int updateHostServiceState(Query *query, const LogEntry *entry,
                               HostServiceState *hs_state, bool only_update);
};

#endif  // TableStateHistory_h
