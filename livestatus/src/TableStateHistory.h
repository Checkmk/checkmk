// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <map>
#include <memory>
#include <string>

#include "LogCache.h"
#include "Logfile.h"
#include "Table.h"
class Column;
class ColumnOffsets;
class Filter;
class HostServiceState;
class LogEntry;
class MonitoringCore;
class Query;
class User;

class TableStateHistory : public Table {
public:
    TableStateHistory(MonitoringCore *mc, LogCache *log_cache);
    static void addColumns(Table *table, const std::string &prefix,
                           const ColumnOffsets &offsets);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query *query, const User &user) override;
    [[nodiscard]] std::shared_ptr<Column> column(
        std::string colname) const override;
    static std::unique_ptr<Filter> createPartialFilter(const Query &query);

private:
    LogCache *_log_cache;
    bool _abort_query;

    enum class ModificationStatus { unchanged, changed };

    void answerQueryInternal(Query *query, const User &user,
                             const LogFiles &log_files);
    const Logfile::map_type *getEntries(Logfile *logfile);
    void getPreviousLogentry(const LogFiles &log_files,
                             LogFiles::const_iterator &it_logs,
                             const Logfile::map_type *&entries,
                             Logfile::const_iterator &it_entries);
    LogEntry *getNextLogentry(const LogFiles &log_files,
                              LogFiles::const_iterator &it_logs,
                              const Logfile::map_type *&entries,
                              Logfile::const_iterator &it_entries);
    void process(Query *query, const User &user,
                 std::chrono::system_clock::duration query_timeframe,
                 HostServiceState *hs_state);
    ModificationStatus updateHostServiceState(
        Query *query, const User &user,
        std::chrono::system_clock::duration query_timeframe,
        const LogEntry *entry, HostServiceState *hs_state, bool only_update,
        const std::map<std::string, int> &notification_periods);
};

#endif  // TableStateHistory_h
