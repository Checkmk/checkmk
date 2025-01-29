// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TableStateHistory_h
#define TableStateHistory_h

#include <cstddef>
#include <map>
#include <memory>
#include <set>
#include <string>

#include "livestatus/Filter.h"
#include "livestatus/HostServiceState.h"
#include "livestatus/LogCache.h"
#include "livestatus/Logfile.h"
#include "livestatus/Table.h"

class ColumnOffsets;
class ICore;
class LogEntry;
class Logger;
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

    bool rewind_to_start(const LogPeriod &period, Logger *logger);
    LogEntry *getNextLogentry();

private:
    void setEntries();

    const LogFiles *log_files_;
    LogFiles::const_iterator it_logs_;
    const Logfile::map_type *entries_{nullptr};
    Logfile::const_iterator it_entries_;
    size_t max_lines_per_log_file_;
};

class ObjectBlacklist {
public:
    ObjectBlacklist(const Query &query, const User &user);
    // TODO(sp) Fix the signature mismatch below: The key can be derived from
    // the state. When this is done, insert() can be merged into accepts().
    [[nodiscard]] bool accepts(const HostServiceState &hss) const;
    [[nodiscard]] bool contains(HostServiceKey key) const;
    void insert(HostServiceKey key);

private:
    const Query *query_;
    const User *user_;
    std::unique_ptr<Filter> filter_;
    std::set<HostServiceKey> blacklist_;
};

class TimePeriods {
public:
    [[nodiscard]] int find(const std::string &name) const;
    void update(const std::string &options);

private:
    std::map<std::string, int> time_periods_;
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

    using state_info_t =
        std::map<HostServiceKey, std::unique_ptr<HostServiceState>>;

private:
    LogCache *log_cache_;
    bool abort_query_;

    class Processor {
    public:
        Processor(Query &query, const User &user, const LogPeriod &period);

        [[nodiscard]] LogPeriod period() const;
        [[nodiscard]] bool process(HostServiceState &hss) const;

    private:
        Query *query_;
        const User *user_;
        const LogPeriod period_;
    };

    enum class ModificationStatus { unchanged, changed };

    void answerQueryInternal(Query &query, const User &user, const ICore &core,
                             LogEntryForwardIterator &it);

    void handle_state_entry(Processor &processor, const ICore &core,
                            const LogEntry *entry, bool only_update,
                            const TimePeriods &time_periods,
                            state_info_t &state_info,
                            ObjectBlacklist &blacklist);

    static HostServiceState *get_state_for_entry(
        const LogPeriod &period, const ICore &core, const LogEntry *entry,
        bool only_update, const TimePeriods &time_periods,
        state_info_t &state_info, ObjectBlacklist &blacklist);

    static void fill_new_state(HostServiceState *hss, const LogEntry *entry,
                               bool only_update,
                               const TimePeriods &time_periods,
                               state_info_t &state_info);

    void handle_timeperiod_transition(Processor &processor, Logger *logger,
                                      const LogEntry *entry, bool only_update,
                                      TimePeriods &time_periods,
                                      const state_info_t &state_info);

    void final_reports(Processor &processor, const state_info_t &state_info);

    ModificationStatus updateHostServiceState(Processor &processor,
                                              const LogEntry *entry,
                                              HostServiceState &hss,
                                              bool only_update,
                                              const TimePeriods &time_periods);
    void process_time_period_transition(Processor &processor, Logger *logger,
                                        const LogEntry &entry,
                                        HostServiceState &hss,
                                        bool only_update);
};

#endif  // TableStateHistory_h
