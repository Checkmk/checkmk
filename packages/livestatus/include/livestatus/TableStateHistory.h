// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include <chrono>
#include <cstddef>
#include <map>
#include <memory>
#include <set>
#include <string>

#include "livestatus/HostServiceState.h"
#include "livestatus/LogCache.h"
#include "livestatus/Logfile.h"
#include "livestatus/Table.h"

class Column;
class ColumnOffsets;
class Filter;
class ICore;
class IHost;
class IService;
class LogEntry;
class Query;
class User;

// TODO(sp) Better name?
class LogEntryForwardIterator {
public:
    LogEntryForwardIterator(const LogFiles &log_files,
                            size_t max_lines_per_log_file)
        : log_files_{&log_files}
        , it_logs_{log_files.end()}
        , max_lines_per_log_file_{max_lines_per_log_file} {}

    const Logfile::map_type *getEntries();
    LogEntry *getNextLogentry();

    const LogFiles *log_files_;
    LogFiles::const_iterator it_logs_;
    const Logfile::map_type *entries_{nullptr};
    Logfile::const_iterator it_entries_;
    size_t max_lines_per_log_file_;
};

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

    using state_info_t =
        std::map<HostServiceKey, std::unique_ptr<HostServiceState>>;

private:
    using notification_periods_t = std::map<std::string, int>;
    using object_blacklist_t = std::set<HostServiceKey>;

    LogCache *log_cache_;
    bool abort_query_;

    enum class ModificationStatus { unchanged, changed };

    void answerQueryInternal(Query &query, const User &user, const ICore &core,
                             LogEntryForwardIterator &it);

    void handle_state_entry(Query &query, const User &user, const ICore &core,
                            std::chrono::system_clock::duration query_timeframe,
                            const LogEntry *entry, bool only_update,
                            const notification_periods_t &notification_periods,
                            bool is_host_entry, state_info_t &state_info,
                            object_blacklist_t &object_blacklist,
                            const Filter &object_filter,
                            std::chrono::system_clock::time_point since);

    static void insert_new_state(
        Query &query, const User &user, const LogEntry *entry, bool only_update,
        const notification_periods_t &notification_periods,
        state_info_t &state_info, object_blacklist_t &object_blacklist,
        const Filter &object_filter,
        std::chrono::system_clock::time_point since, const IHost *entry_host,
        const IService *entry_service, HostServiceKey key);

    void handle_timeperiod_transition(
        Query &query, const User &user, const ICore &core,
        std::chrono::system_clock::duration query_timeframe,
        const LogEntry *entry, bool only_update,
        notification_periods_t &notification_periods,
        const state_info_t &state_info);

    void final_reports(Query &query, const User &user,
                       std::chrono::system_clock::duration query_timeframe,
                       const state_info_t &state_info,
                       std::chrono::system_clock::time_point until);

    void process(Query &query, const User &user,
                 std::chrono::system_clock::duration query_timeframe,
                 HostServiceState &hss);

    void update(Query &query, const User &user, const ICore &core,
                std::chrono::system_clock::duration query_timeframe,
                const LogEntry *entry, HostServiceState &state,
                bool only_update,
                const notification_periods_t &notification_periods);

    ModificationStatus updateHostServiceState(
        Query &query, const User &user, const ICore &core,
        std::chrono::system_clock::duration query_timeframe,
        const LogEntry *entry, HostServiceState &hss, bool only_update,
        const notification_periods_t &notification_periods);
};

#endif  // TableStateHistory_h
