// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableStateHistory.h"

#include <bitset>
#include <chrono>
#include <compare>
#include <cstdlib>
#include <stdexcept>
#include <utility>
#include <vector>

#include "livestatus/ChronoUtils.h"
#include "livestatus/Column.h"
#include "livestatus/DoubleColumn.h"
#include "livestatus/ICore.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/LogEntry.h"
#include "livestatus/Logger.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"
#include "livestatus/StringUtils.h"
#include "livestatus/TableHosts.h"
#include "livestatus/TableServices.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/User.h"

using row_type = HostServiceState;

using namespace std::chrono_literals;

TableStateHistory::TableStateHistory(LogCache *log_cache)
    : log_cache_{log_cache}, abort_query_{false} {
    addColumns(this, "", ColumnOffsets{});
}

// static
void TableStateHistory::addColumns(Table *table, const std::string &prefix,
                                   const ColumnOffsets &offsets) {
    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "time", "Time of the log event (seconds since 1/1/1970)",
        offsets, [](const row_type &row) { return row._time; }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "lineno", "The number of the line in the log file", offsets,
        [](const row_type &row) { return row._lineno; }));
    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "from", "Start time of state (seconds since 1/1/1970)",
        offsets, [](const row_type &row) { return row._from; }));
    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "until", "End time of state (seconds since 1/1/1970)", offsets,
        [](const row_type &row) { return row._until; }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "duration", "Duration of state (until - from)", offsets,
        [](const row_type &row) {
            return mk::ticks<std::chrono::seconds>(row._duration);
        }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "duration_part",
        "Duration part in regard to the query timeframe", offsets,
        [](const row_type &row) { return row._duration_part; }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "state",
        "The state of the host or service in question - OK(0) / WARNING(1) / CRITICAL(2) / UNKNOWN(3) / UNMONITORED(-1)",
        offsets, [](const row_type &row) { return row._state; }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "host_down", "Shows if the host of this service is down",
        offsets, [](const row_type &row) { return row._host_down; }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "in_downtime", "Shows if the host or service is in downtime",
        offsets, [](const row_type &row) { return row._in_downtime; }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "in_host_downtime",
        "Shows if the host of this service is in downtime", offsets,
        [](const row_type &row) { return row._in_host_downtime; }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "is_flapping", "Shows if the host or service is flapping",
        offsets, [](const row_type &row) { return row._is_flapping; }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "in_notification_period",
        "Shows if the host or service is within its notification period",
        offsets,
        [](const row_type &row) { return row._in_notification_period; }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "notification_period",
        "The notification period of the host or service in question", offsets,
        [](const row_type &row) { return row._notification_period; }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "in_service_period",
        "Shows if the host or service is within its service period", offsets,
        [](const row_type &row) { return row._in_service_period; }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "service_period",
        "The service period of the host or service in question", offsets,
        [](const row_type &row) { return row._service_period; }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "debug_info", "Debug information", offsets,
        [](const row_type &row) { return row._debug_info; }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "host_name", "Host name", offsets,
        [](const row_type &row) { return row._host_name; }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "service_description", "Description of the service", offsets,
        [](const row_type &row) { return row._service_description; }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "log_output", "Logfile output relevant for this state",
        offsets, [](const row_type &row) { return row._log_output; }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "long_log_output",
        "Complete logfile output relevant for this state", offsets,
        [](const row_type &row) { return row._long_log_output; }));

    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "duration_ok", "OK duration of state ( until - from )",
        offsets, [](const row_type &row) {
            return mk::ticks<std::chrono::seconds>(row._duration_ok);
        }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "duration_part_ok",
        "OK duration part in regard to the query timeframe", offsets,
        [](const row_type &row) { return row._duration_part_ok; }));

    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "duration_warning", "WARNING duration of state (until - from)",
        offsets, [](const row_type &row) {
            return mk::ticks<std::chrono::seconds>(row._duration_warning);
        }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "duration_part_warning",
        "WARNING duration part in regard to the query timeframe", offsets,
        [](const row_type &row) { return row._duration_part_warning; }));

    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "duration_critical",
        "CRITICAL duration of state (until - from)", offsets,
        [](const row_type &row) {
            return mk::ticks<std::chrono::seconds>(row._duration_critical);
        }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "duration_part_critical",
        "CRITICAL duration part in regard to the query timeframe", offsets,
        [](const row_type &row) { return row._duration_part_critical; }));

    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "duration_unknown", "UNKNOWN duration of state (until - from)",
        offsets, [](const row_type &row) {
            return mk::ticks<std::chrono::seconds>(row._duration_unknown);
        }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "duration_part_unknown",
        "UNKNOWN duration part in regard to the query timeframe", offsets,
        [](const row_type &row) { return row._duration_part_unknown; }));

    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "duration_unmonitored",
        "UNMONITORED duration of state (until - from)", offsets,
        [](const row_type &row) {
            return mk::ticks<std::chrono::seconds>(row._duration_unmonitored);
        }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "duration_part_unmonitored",
        "UNMONITORED duration part in regard to the query timeframe", offsets,
        [](const row_type &row) { return row._duration_part_unmonitored; }));

    // join host and service tables
    TableHosts::addColumns(
        table, prefix + "current_host_",
        offsets.add([](Row r) { return r.rawData<row_type>()->_host; }),
        LockComments::yes, LockDowntimes::yes);
    TableServices::addColumns(
        table, prefix + "current_service_",
        offsets.add([](Row r) { return r.rawData<row_type>()->_service; }),
        TableServices::AddHosts::no, LockComments::yes, LockDowntimes::yes);
}

std::string TableStateHistory::name() const { return "statehist"; }

std::string TableStateHistory::namePrefix() const { return "statehist_"; }

void LogEntryForwardIterator::setEntries() {
    entries_ = it_logs_->second->getEntriesFor(
        {
            .max_lines_per_log_file = max_lines_per_log_file_,
            .log_entry_classes =
                LogEntryClasses{}
                    .set(static_cast<int>(LogEntry::Class::alert))
                    .set(static_cast<int>(LogEntry::Class::program))
                    .set(static_cast<int>(LogEntry::Class::state)),
        },
        max_cached_messages_);
    it_entries_ = entries_->begin();
}

LogEntry *LogEntryForwardIterator::getNextLogentry() {
    if (it_entries_ != entries_->end()) {
        ++it_entries_;
    }

    while (it_entries_ == entries_->end()) {
        auto it_logs_cpy = it_logs_;
        if (++it_logs_cpy == log_files_->end()) {
            return nullptr;
        }
        ++it_logs_;
        setEntries();
    }
    return it_entries_->second.get();
}

namespace {
class TimePeriodTransition {
public:
    explicit TimePeriodTransition(const std::string &str) {
        auto fields = mk::split(str, ';');
        if (fields.size() != 3) {
            throw std::invalid_argument("expected 3 arguments");
        }
        name_ = fields[0];
        from_ = std::stoi(fields[1]);
        to_ = std::stoi(fields[2]);
    }

    [[nodiscard]] std::string name() const { return name_; }
    [[nodiscard]] int from() const { return from_; }
    [[nodiscard]] int to() const { return to_; }

private:
    std::string name_;
    int from_;
    int to_;
};
}  // namespace

void TableStateHistory::answerQuery(Query &query, const User &user,
                                    const ICore &core) {
    log_cache_->apply(
        core.paths()->history_file(), core.paths()->history_archive_directory(),
        core.last_logfile_rotation(),
        [this, &query, &user, &core](const LogFiles &log_files,
                                     size_t /*num_cached_log_messages*/) {
            LogEntryForwardIterator it{log_files, core.maxLinesPerLogFile(),
                                       core.maxCachedMessages()};
            answerQueryInternal(query, user, core, it);
        });
}

namespace {
// Set still unknown hosts / services to unmonitored
void set_unknown_to_unmonitored(
    const TableStateHistory::state_info_t &state_info) {
    for (const auto &[_, hss] : state_info) {
        if (hss->_may_no_longer_exist) {
            hss->_has_vanished = true;
        }
    }
}

void handle_log_initial_states(
    const TableStateHistory::state_info_t &state_info,
    std::chrono::system_clock::time_point entry_time) {
    // This feature is only available if log_initial_states is set to 1. If
    // log_initial_states is set, each nagios startup logs the initial states of
    // all known hosts and services. Therefore we can detect if a host is no
    // longer available after a nagios startup. If it still exists an INITIAL
    // HOST/SERVICE state entry will follow up shortly.
    for (const auto &[_, hss] : state_info) {
        if (!hss->_has_vanished) {
            hss->_last_known_time = entry_time;
            hss->_may_no_longer_exist = true;
        }
    }
}
}  // namespace

bool LogEntryForwardIterator::rewind_to_start(const LogPeriod &period,
                                              Logger *logger) {
    if (log_files_->begin() == log_files_->end()) {
        Debug(logger) << "no log files found";
        return false;
    }

    // Switch to last logfile (we have at least one)
    --it_logs_;
    auto newest_log = it_logs_;

    // Now find the log where 'since' starts.
    while (it_logs_ != log_files_->begin() &&
           it_logs_->second->since() >= period.since) {
        --it_logs_;  // go back in history
    }

    if (it_logs_->second->since() >= period.until) {
        Debug(logger) << "all log files are newer than " << period;
        return false;
    }

    // Now it_logs points to the newest log file that starts strictly before the
    // query period. If there is no such log file, it points to the first one.
    // In other words, we are at the newest log file with the guarantee that
    // older log files do not contain entries withing the query period.
    Debug(logger) << "starting state history computation at "
                  << *it_logs_->second;

    // Determine initial log entry, setting entries_ and it_entries_
    setEntries();
    // If the last entry is older than the start of the query period, then
    // ignore this log file. Well, almost...
    if (!entries_->empty() && it_logs_ != newest_log &&
        ((--entries_->end()) == entries_->begin() ||
         (--entries_->end())->second->time() < period.since)) {
        it_entries_ = --entries_->end();  // TODO(sp) Is the decrement an error?
    }
    return true;
}

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
void TableStateHistory::answerQueryInternal(Query &query, const User &user,
                                            const ICore &core,
                                            LogEntryForwardIterator &it) {
    ObjectBlacklist blacklist{query, user};

    // This flag might be set to true by the return value of processDataset(...)
    abort_query_ = false;

    // Keep track of the historic state of services/hosts here
    state_info_t state_info;

    auto *logger = core.loggerLivestatus();
    const auto period = LogPeriod::make(query);
    if (period.empty()) {
        Debug(logger) << "empty query period " << period;
        return;
    }

    if (!it.rewind_to_start(period, logger)) {
        return;
    }

    Processor processor{query, user, period};

    // From now on use getNextLogentry()
    bool only_update = true;
    bool in_nagios_initial_states = false;

    // Notification periods information, name: active(1)/inactive(0)
    TimePeriods time_periods;

    // NOLINTNEXTLINE(misc-const-correctness)
    while (LogEntry *entry = it.getNextLogentry()) {
        if (abort_query_ || entry->time() >= period.until) {
            break;
        }

        if (only_update && entry->time() >= period.since) {
            // Reached start of query timeframe. From now on let's produce real
            // output. Update _from time of every state entry
            for (const auto &[_, hss] : state_info) {
                hss->_from = period.since;
                hss->_until = period.since;
            }
            only_update = false;
        }

        switch (entry->kind()) {
            case LogEntryKind::none:
            case LogEntryKind::core_starting:
            case LogEntryKind::core_stopping:
            case LogEntryKind::log_version:
            case LogEntryKind::host_acknowledge_alert:
            case LogEntryKind::service_acknowledge_alert:
                if (in_nagios_initial_states) {
                    set_unknown_to_unmonitored(state_info);
                }
                in_nagios_initial_states = false;
                break;
            case LogEntryKind::initial_service_state:
                handle_state_entry(processor, core, entry, only_update,
                                   time_periods, state_info, blacklist);
                break;
            case LogEntryKind::service_alert:
            case LogEntryKind::current_service_state:
            case LogEntryKind::service_downtime_alert:
            case LogEntryKind::service_flapping_alert:
                if (in_nagios_initial_states) {
                    set_unknown_to_unmonitored(state_info);
                }
                handle_state_entry(processor, core, entry, only_update,
                                   time_periods, state_info, blacklist);
                in_nagios_initial_states = false;
                break;
            case LogEntryKind::initial_host_state:
                handle_state_entry(processor, core, entry, only_update,
                                   time_periods, state_info, blacklist);
                break;
            case LogEntryKind::host_alert:
            case LogEntryKind::current_host_state:
            case LogEntryKind::host_downtime_alert:
            case LogEntryKind::host_flapping_alert:
                if (in_nagios_initial_states) {
                    set_unknown_to_unmonitored(state_info);
                }
                handle_state_entry(processor, core, entry, only_update,
                                   time_periods, state_info, blacklist);
                in_nagios_initial_states = false;
                break;
            case LogEntryKind::timeperiod_transition:
                if (in_nagios_initial_states) {
                    set_unknown_to_unmonitored(state_info);
                }
                handle_timeperiod_transition(processor, logger, entry,
                                             only_update, time_periods,
                                             state_info);
                in_nagios_initial_states = false;
                break;
            case LogEntryKind::logging_initial_states:
                if (in_nagios_initial_states) {
                    set_unknown_to_unmonitored(state_info);
                }
                handle_log_initial_states(state_info, entry->time());
                in_nagios_initial_states = true;
                break;
        }
    }

    if (!abort_query_) {
        final_reports(processor, state_info);
    }
}

void TableStateHistory::handle_state_entry(
    Processor &processor, const ICore &core, const LogEntry *entry,
    bool only_update, const TimePeriods &time_periods, state_info_t &state_info,
    ObjectBlacklist &blacklist) {
    auto *hss =
        get_state_for_entry(processor.period(), core, entry, only_update,
                            time_periods, state_info, blacklist);
    if (hss == nullptr) {
        return;
    }
    auto state_changed = updateHostServiceState(processor, entry, *hss,
                                                only_update, time_periods);
    // Host downtime or state changes also affect its services
    if (entry->kind() == LogEntryKind::host_alert ||
        entry->kind() == LogEntryKind::current_host_state ||
        entry->kind() == LogEntryKind::host_downtime_alert) {
        if (state_changed == ModificationStatus::changed) {
            for (auto &svc : hss->_services) {
                updateHostServiceState(processor, entry, *svc, only_update,
                                       time_periods);
            }
        }
    }
}

// static
HostServiceState *TableStateHistory::get_state_for_entry(
    const LogPeriod &period, const ICore &core, const LogEntry *entry,
    bool only_update, const TimePeriods &time_periods, state_info_t &state_info,
    ObjectBlacklist &blacklist) {
    const auto *entry_host = core.find_host(entry->host_name());
    const auto *entry_service =
        core.find_service(entry->host_name(), entry->service_description());

    HostServiceKey key =
        entry->service_description().empty()
            ? (entry_host == nullptr ? nullptr
                                     : entry_host->handleForStateHistory())
            : (entry_service == nullptr
                   ? nullptr
                   : entry_service->handleForStateHistory());
    if (key == nullptr) {
        return nullptr;
    }

    if (blacklist.contains(key)) {
        // Host/Service is not needed for this query and has already been
        // filtered out.
        return nullptr;
    }

    if (!state_info.contains(key)) {
        auto hss = std::make_unique<HostServiceState>();
        hss->_is_host = entry->service_description().empty();
        hss->_host = entry_host;
        hss->_service = entry_service;
        hss->_host_name = entry->host_name();
        hss->_service_description = entry->service_description();
        hss->_from = period.since;

        // No state found. Now check if this host/services is filtered out.
        // Note: we currently do not filter out hosts since they might be needed
        // for service states
        if (!hss->_is_host) {
            // NOTE: The filter is only allowed to inspect those fields of state
            // which are set by now, see createPartialFilter()!
            if (!blacklist.accepts(*hss, core)) {
                blacklist.insert(key);
                return nullptr;
            }
        }

        fill_new_state(hss.get(), entry, only_update, time_periods, state_info);
        state_info[key] = std::move(hss);
    }
    return state_info[key].get();
}

// static
void TableStateHistory::fill_new_state(HostServiceState *hss,
                                       const LogEntry *entry, bool only_update,
                                       const TimePeriods &time_periods,
                                       state_info_t &state_info) {
    // Host/Service relations
    if (hss->_is_host) {
        for (const auto &[_, s] : state_info) {
            if (s->_host != nullptr &&
                s->_host->handleForStateHistory() ==
                    hss->_host->handleForStateHistory()) {
                hss->_services.push_back(s.get());
            }
        }
    } else {
        auto it_inh = state_info.find(hss->_host->handleForStateHistory());
        if (it_inh != state_info.end()) {
            it_inh->second->_services.push_back(hss);
        }
    }

    // Get notification period of host/service. If this host/service is no
    // longer available in nagios -> set to ""
    hss->_notification_period =
        hss->_service != nullptr ? hss->_service->notificationPeriodName()
        : hss->_host != nullptr  ? hss->_host->notificationPeriodName()
                                 : "";
    hss->_in_notification_period = time_periods.find(hss->_notification_period);

    // Same for service period.
    hss->_service_period =
        hss->_service != nullptr ? hss->_service->servicePeriodName()
        : hss->_host != nullptr  ? hss->_host->servicePeriodName()
                                 : "";
    hss->_in_service_period = time_periods.find(hss->_service_period);

    // If this key is a service try to find its host and apply its
    // _in_host_downtime and _host_down parameters
    if (!hss->_is_host) {
        auto my_host = state_info.find(hss->_host->handleForStateHistory());
        if (my_host != state_info.end()) {
            hss->_in_host_downtime = my_host->second->_in_host_downtime;
            hss->_host_down = my_host->second->_host_down;
        }
    }

    // Log UNMONITORED state if this host or service just appeared within the
    // query timeframe. It gets a grace period of ten minutes (Nagios startup).
    // Note that _from is at the beginning of the requested log period for fresh
    // states.
    if (!only_update && entry->time() - hss->_from > 10min) {
        hss->_debug_info = "UNMONITORED ";
        hss->_state = -1;
    }
}

void TableStateHistory::handle_timeperiod_transition(
    Processor &processor, Logger *logger, const LogEntry *entry,
    bool only_update, TimePeriods &time_periods,
    const state_info_t &state_info) {
    try {
        time_periods.update(entry->options());
        for (const auto &[_, hss] : state_info) {
            process_time_period_transition(processor, logger, *entry, *hss,
                                           only_update);
        }
    } catch (const std::logic_error &e) {
        Warning(logger) << "Error: Invalid syntax of TIMEPERIOD TRANSITION: "
                        << entry->message();
    }
}

void TableStateHistory::final_reports(Processor &processor,
                                      const state_info_t &state_info) {
    for (const auto &[_, hss] : state_info) {
        // No trace since the last two nagios startup -> host/service has
        // vanished
        if (hss->_may_no_longer_exist) {
            // Log last known state up to nagios restart
            hss->_time = hss->_last_known_time;
            hss->_until = hss->_last_known_time;
            abort_query_ = processor.process(*hss);

            // Set absent state
            hss->_state = -1;
            hss->_debug_info = "UNMONITORED";
            hss->_log_output = "";
            hss->_long_log_output = "";
        }

        // A slight hack: We put the final HostServiceStates a tiny bit before
        // the end of the query period. Conceptually, they are exactly at
        // period.until, but rows with such a timestamp would get filtered out:
        // The query period is a half-open interval.
        hss->_time = processor.period().until - 1s;
        hss->_until = hss->_time;

        abort_query_ = processor.process(*hss);
    }
}

void TableStateHistory::process_time_period_transition(Processor &processor,
                                                       Logger *logger,
                                                       const LogEntry &entry,
                                                       HostServiceState &hss,
                                                       bool only_update) {
    // Update basic information
    hss._time = entry.time();
    hss._lineno = entry.lineno();
    hss._until = entry.time();

    try {
        const TimePeriodTransition tpt{entry.options()};
        // if no _host pointer is available the initial status of
        // _in_notification_period (1) never changes
        if (hss._host != nullptr && tpt.name() == hss._notification_period) {
            if (tpt.to() != hss._in_notification_period) {
                if (!only_update) {
                    abort_query_ = processor.process(hss);
                }
                hss._debug_info = "TIMEPERIOD ";
                hss._in_notification_period = tpt.to();
            }
        }
        // same for service period
        if (hss._host != nullptr && tpt.name() == hss._service_period) {
            if (tpt.to() != hss._in_service_period) {
                if (!only_update) {
                    abort_query_ = processor.process(hss);
                }
                hss._debug_info = "TIMEPERIOD ";
                hss._in_service_period = tpt.to();
            }
        }
    } catch (const std::logic_error &e) {
        Warning(logger) << "Error: Invalid syntax of TIMEPERIOD TRANSITION: "
                        << entry.message();
    }
}

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
TableStateHistory::ModificationStatus TableStateHistory::updateHostServiceState(
    Processor &processor, const LogEntry *entry, HostServiceState &hss,
    bool only_update, const TimePeriods &time_periods) {
    ModificationStatus state_changed{ModificationStatus::changed};

    // Revive host / service if it was unmonitored
    if (hss._has_vanished) {
        hss._time = hss._last_known_time;
        hss._until = hss._last_known_time;
        if (!only_update) {
            abort_query_ = processor.process(hss);
        }

        hss._may_no_longer_exist = false;
        hss._has_vanished = false;
        // Set absent state
        hss._state = -1;
        hss._debug_info = "UNMONITORED";
        hss._in_downtime = false;
        hss._in_notification_period = 0;
        hss._in_service_period = 0;
        hss._is_flapping = false;
        hss._log_output = "";
        hss._long_log_output = "";

        // Apply latest notification period information and set the host_state
        // to unmonitored
        hss._in_notification_period =
            time_periods.find(hss._notification_period);
        hss._in_service_period = time_periods.find(hss._service_period);
    }

    // Update basic information
    hss._time = entry->time();
    hss._lineno = entry->lineno();
    hss._until = entry->time();
    hss._may_no_longer_exist = false;

    switch (entry->kind()) {
        case LogEntryKind::none:
        case LogEntryKind::core_starting:
        case LogEntryKind::core_stopping:
        case LogEntryKind::log_version:
        case LogEntryKind::logging_initial_states:
        case LogEntryKind::host_acknowledge_alert:
        case LogEntryKind::service_acknowledge_alert:
        case LogEntryKind::timeperiod_transition:
            abort();  // should not happen
            break;
        case LogEntryKind::current_host_state:
        case LogEntryKind::initial_host_state:
        case LogEntryKind::host_alert: {
            if (hss._is_host) {
                if (hss._state != entry->state()) {
                    if (!only_update) {
                        abort_query_ = processor.process(hss);
                    }
                    hss._state = entry->state();
                    hss._host_down = entry->state() > 0;
                    hss._debug_info = "HOST STATE";
                } else {
                    state_changed = ModificationStatus::unchanged;
                }
            } else if (hss._host_down != (entry->state() > 0)) {
                if (!only_update) {
                    abort_query_ = processor.process(hss);
                }
                hss._host_down = entry->state() > 0;
                hss._debug_info = "SVC HOST STATE";
            }
            break;
        }
        case LogEntryKind::current_service_state:
        case LogEntryKind::initial_service_state:
        case LogEntryKind::service_alert: {
            if (hss._state != entry->state()) {
                if (!only_update) {
                    abort_query_ = processor.process(hss);
                }
                hss._debug_info = "SVC ALERT";
                hss._state = entry->state();
            }
            break;
        }
        case LogEntryKind::host_downtime_alert: {
            const bool downtime_active =
                entry->state_type().starts_with("STARTED");

            if (hss._in_host_downtime != downtime_active) {
                if (!only_update) {
                    abort_query_ = processor.process(hss);
                }
                hss._debug_info =
                    hss._is_host ? "HOST DOWNTIME" : "SVC HOST DOWNTIME";
                hss._in_host_downtime = downtime_active;
                if (hss._is_host) {
                    hss._in_downtime = downtime_active;
                }
            } else {
                state_changed = ModificationStatus::unchanged;
            }
            break;
        }
        case LogEntryKind::service_downtime_alert: {
            const bool downtime_active =
                entry->state_type().starts_with("STARTED");
            if (hss._in_downtime != downtime_active) {
                if (!only_update) {
                    abort_query_ = processor.process(hss);
                }
                hss._debug_info = "DOWNTIME SERVICE";
                hss._in_downtime = downtime_active;
            }
            break;
        }
        case LogEntryKind::host_flapping_alert:
        case LogEntryKind::service_flapping_alert: {
            const bool flapping_active =
                entry->state_type().starts_with("STARTED");
            if (hss._is_flapping != flapping_active) {
                if (!only_update) {
                    abort_query_ = processor.process(hss);
                }
                hss._debug_info = "FLAPPING ";
                hss._is_flapping = flapping_active;
            } else {
                state_changed = ModificationStatus::unchanged;
            }
            break;
        }
    }

    const bool fix_me =
        (entry->kind() == LogEntryKind::initial_host_state ||
         entry->kind() == LogEntryKind::initial_service_state) &&
        entry->plugin_output() == "(null)";
    hss._log_output = fix_me ? "" : entry->plugin_output();
    hss._long_log_output = entry->long_plugin_output();

    return state_changed;
}

std::shared_ptr<Column> TableStateHistory::column(std::string colname,
                                                  const ICore &core) const {
    try {
        // First try to find column in the usual way
        return Table::column(colname, core);
    } catch (const std::runtime_error &e) {
        // Now try with prefix "current_", since our joined tables have this
        // prefix in order to make clear that we access current and not historic
        // data and in order to prevent mixing up historic and current fields
        // with the same name.
        return Table::column("current_" + colname, core);
    }
}

TableStateHistory::Processor::Processor(Query &query, const User &user,
                                        const LogPeriod &period)
    : query_{&query}, user_{&user}, period_{period} {}

LogPeriod TableStateHistory::Processor::period() const { return period_; }

bool TableStateHistory::Processor::process(HostServiceState &hss) const {
    hss.computePerStateDurations(period_.duration());

    // if (hss._duration > 0)
    auto abort_query =
        user_->is_authorized_for_object(hss._host, hss._service, false) &&
        !query_->processDataset(Row{&hss});

    hss._from = hss._until;
    return abort_query;
}

ObjectBlacklist::ObjectBlacklist(const Query &query, const User &user)
    : query_{&query}
    , user_{&user}
    , filter_{query.partialFilter(
          "current host/service columns", [](const std::string &columnName) {
              // NOTE: This is quite brittle and must be kept in sync with its
              // usage in TableStateHistory::get_state_for_entry()!
              return (
                  // joined via HostServiceState::_host
                  columnName.starts_with("current_host_") ||
                  // joined via HostServiceState::_service
                  columnName.starts_with("current_service_") ||
                  // HostServiceState::_host_name
                  columnName == "host_name" ||
                  // HostServiceState::_service_description
                  columnName == "service_description");
          })} {}

bool ObjectBlacklist::accepts(const HostServiceState &hss,
                              const ICore &core) const {
    return filter_->accepts(Row{&hss}, *user_, query_->timezoneOffset(), core);
}

bool ObjectBlacklist::contains(HostServiceKey key) const {
    return blacklist_.contains(key);
}

void ObjectBlacklist::insert(HostServiceKey key) { blacklist_.insert(key); }

int TimePeriods::find(const std::string &name) const {
    auto it = time_periods_.find(name);
    // no info => defaults to "within period"
    return it == time_periods_.end() ? 1 : it->second;
}

void TimePeriods::update(const std::string &options) {
    const TimePeriodTransition tpt{options};
    time_periods_[tpt.name()] = tpt.to();
}
