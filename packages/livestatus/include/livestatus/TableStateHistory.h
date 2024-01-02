// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include <chrono>
#include <map>
#include <memory>
#include <string>

#include "livestatus/Table.h"

class Column;
class ColumnOffsets;
class Filter;
class HostServiceState;
class ICore;
class LogCache;
class LogEntry;
class LogFiles;
class Query;
class User;

class TableStateHistory : public Table {
public:
    TableStateHistory(ICore *mc, LogCache *log_cache);
    static void addColumns(Table *table, const ICore &core,
                           const std::string &prefix,
                           const ColumnOffsets &offsets);

    [[nodiscard]] std::string name() const override;
    [[nodiscard]] std::string namePrefix() const override;
    void answerQuery(Query &query, const User &user,
                     const ICore &core) override;
    [[nodiscard]] std::shared_ptr<Column> column(
        std::string colname) const override;
    static std::unique_ptr<Filter> createPartialFilter(const Query &query);

private:
    LogCache *log_cache_;
    bool abort_query_;

    enum class ModificationStatus { unchanged, changed };

    void answerQueryInternal(Query &query, const User &user, const ICore &core,
                             const LogFiles &log_files);
    void process(Query &query, const User &user,
                 std::chrono::system_clock::duration query_timeframe,
                 HostServiceState *hss);
    ModificationStatus updateHostServiceState(
        Query &query, const User &user, const ICore &core,
        std::chrono::system_clock::duration query_timeframe,
        const LogEntry *entry, HostServiceState *hss, bool only_update,
        const std::map<std::string, int> &notification_periods);
};

#endif  // TableStateHistory_h
