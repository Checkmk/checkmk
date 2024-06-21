// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableStateHistory.h"

#include <bitset>
#include <compare>
#include <cstddef>
#include <optional>
#include <ratio>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

#include "livestatus/ChronoUtils.h"
#include "livestatus/Column.h"
#include "livestatus/DoubleColumn.h"
#include "livestatus/Filter.h"
#include "livestatus/HostServiceState.h"
#include "livestatus/ICore.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/LogCache.h"
#include "livestatus/LogEntry.h"
#include "livestatus/Logfile.h"
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

enum {
    STATE_OK = 0,
    STATE_WARNING = 1,
    STATE_CRITICAL = 2,
    STATE_UNKNOWN = 3,
};

using namespace std::chrono_literals;

TableStateHistory::TableStateHistory(ICore *mc, LogCache *log_cache)
    : log_cache_{log_cache} {
    addColumns(this, *mc, "", ColumnOffsets{});
}

// static
void TableStateHistory::addColumns(Table *table, const ICore &core,
                                   const std::string &prefix,
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
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "host_down", "Shows if the host of this service is down",
        offsets, [](const row_type &row) { return row._host_down; }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "in_downtime", "Shows if the host or service is in downtime",
        offsets, [](const row_type &row) { return row._in_downtime; }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "in_host_downtime",
        "Shows if the host of this service is in downtime", offsets,
        [](const row_type &row) { return row._in_host_downtime; }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
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
        table, core, prefix + "current_host_",
        offsets.add([](Row r) { return r.rawData<row_type>()->_host; }),
        LockComments::yes, LockDowntimes::yes);
    TableServices::addColumns(
        table, core, prefix + "current_service_",
        offsets.add([](Row r) { return r.rawData<row_type>()->_service; }),
        TableServices::AddHosts::no, LockComments::yes, LockDowntimes::yes);
}

std::string TableStateHistory::name() const { return "statehist"; }

std::string TableStateHistory::namePrefix() const { return "statehist_"; }

namespace {
const Logfile::map_type *getEntries(Logfile *logfile,
                                    size_t max_lines_per_log_file) {
    return logfile->getEntriesFor({
        .max_lines_per_log_file = max_lines_per_log_file,
        .log_entry_classes =
            std::bitset<32>{}
                .set(static_cast<int>(LogEntry::Class::alert))
                .set(static_cast<int>(LogEntry::Class::program))
                .set(static_cast<int>(LogEntry::Class::state)),
        .since = {},  // TODO(sp)
        .until = {},  // TODO(sp)
    });
}

void getPreviousLogentry(const LogFiles &log_files,
                         LogFiles::const_iterator &it_logs,
                         const Logfile::map_type *&entries,
                         Logfile::const_iterator &it_entries,
                         size_t max_lines_per_log_file) {
    while (it_entries == entries->begin()) {
        // open previous logfile
        if (it_logs == log_files.begin()) {
            return;
        }
        --it_logs;
        entries = getEntries(it_logs->second.get(), max_lines_per_log_file);
        it_entries = entries->end();
    }
    --it_entries;
}

LogEntry *getNextLogentry(const LogFiles &log_files,
                          LogFiles::const_iterator &it_logs,
                          const Logfile::map_type *&entries,
                          Logfile::const_iterator &it_entries,
                          size_t max_lines_per_log_file) {
    if (it_entries != entries->end()) {
        ++it_entries;
    }

    while (it_entries == entries->end()) {
        auto it_logs_cpy = it_logs;
        if (++it_logs_cpy == log_files.end()) {
            return nullptr;
        }
        ++it_logs;
        entries = getEntries(it_logs->second.get(), max_lines_per_log_file);
        it_entries = entries->begin();
    }
    return it_entries->second.get();
}

class TimeperiodTransition {
public:
    explicit TimeperiodTransition(const std::string &str) {
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

// Create a partial filter, that contains only such filters that check
// attributes of current hosts and services

// static
std::unique_ptr<Filter> TableStateHistory::createPartialFilter(
    const Query &query) {
    return query.partialFilter("current host/service columns",
                               [](const std::string &columnName) {
                                   return columnName.starts_with("current_") ||
                                          columnName.starts_with("host_") ||
                                          columnName.starts_with("service_");
                               });
}

void TableStateHistory::answerQuery(Query &query, const User &user,
                                    const ICore &core) {
    log_cache_->apply(
        [this, &query, &user, &core](const LogFiles &log_cache,
                                     size_t /*num_cached_log_messages*/) {
            answerQueryInternal(query, user, core, log_cache);
        });
}

void TableStateHistory::answerQueryInternal(Query &query, const User &user,
                                            const ICore &core,
                                            const LogFiles &log_files) {
    if (log_files.begin() == log_files.end()) {
        return;
    }
    auto object_filter = createPartialFilter(query);

    // This flag might be set to true by the return value of processDataset(...)
    abort_query_ = false;

    // Keep track of the historic state of services/hosts here
    std::map<HostServiceKey, HostServiceState *> state_info;

    // Store hosts/services that we have filtered out here
    std::set<HostServiceKey> object_blacklist;

    // Optimize time interval for the query. In log queries there should always
    // be a time range in form of one or two filter expressions over time. We
    // use that to limit the number of logfiles we need to scan and to find the
    // optimal entry point into the logfile
    auto glb = query.greatestLowerBoundFor("time");
    if (!glb) {
        query.invalidRequest(
            "Start of timeframe required. e.g. Filter: time > 1234567890");
        return;
    }
    // NOTE: Both time points are *inclusive*, i.e. we have a closed interval,
    // which is quite awkward: Half-open intervals are the way to go!
    auto since = std::chrono::system_clock::from_time_t(*glb);

    auto lub = query.leastUpperBoundFor("time");
    auto until = (lub ? std::chrono::system_clock::from_time_t(*lub)
                      : std::chrono::system_clock::now()) +
                 1s;

    // NOTE: We have a closed interval with a resolution of 1s, so we have
    // to subtract 1s to get the duration. Silly representation...
    auto query_timeframe = until - since - 1s;
    if (query_timeframe <= 0s) {
        return;
    }

    // Switch to last logfile (we have at least one)
    LogFiles::const_iterator it_logs{log_files.end()};
    --it_logs;
    auto newest_log = it_logs;

    // Now find the log where 'since' starts.
    while (it_logs != log_files.begin() && it_logs->second->since() >= since) {
        --it_logs;  // go back in history
    }

    // Check if 'until' is within these logfiles
    if (it_logs->second->since() > until) {
        // All logfiles are too new, invalid timeframe
        // -> No data available. Return empty result.
        return;
    }

    // Determine initial logentry
    auto max_lines_per_log_file = core.maxLinesPerLogFile();
    const auto *entries =
        getEntries(it_logs->second.get(), max_lines_per_log_file);
    Logfile::const_iterator it_entries;
    if (!entries->empty() && it_logs != newest_log) {
        it_entries = entries->end();
        // Check last entry. If it's younger than _since -> use this logfile too
        if (--it_entries != entries->begin()) {
            if (it_entries->second->time() >= since) {
                it_entries = entries->begin();
            }
        }
    } else {
        it_entries = entries->begin();
    }

    // From now on use getPreviousLogentry() / getNextLogentry()
    bool only_update = true;
    bool in_nagios_initial_states = false;

    // Notification periods information, name: active(1)/inactive(0)
    std::map<std::string, int> notification_periods;

    while (LogEntry *entry =
               getNextLogentry(log_files, it_logs, entries, it_entries,
                               max_lines_per_log_file)) {
        if (abort_query_) {
            break;
        }

        if (entry->time() >= until) {
            getPreviousLogentry(log_files, it_logs, entries, it_entries,
                                max_lines_per_log_file);
            break;
        }
        if (only_update && entry->time() >= since) {
            // Reached start of query timeframe. From now on let's produce real
            // output. Update _from time of every state entry
            for (const auto &[key, hst] : state_info) {
                hst->_from = since;
                hst->_until = since;
            }
            only_update = false;
        }

        if (in_nagios_initial_states &&
            entry->kind() != LogEntryKind::state_service_initial &&
            entry->kind() != LogEntryKind::state_host_initial) {
            // Set still unknown hosts / services to unmonitored
            for (const auto &[key, hst] : state_info) {
                if (hst->_may_no_longer_exist) {
                    hst->_has_vanished = true;
                }
            }
            in_nagios_initial_states = false;
        }

        HostServiceKey key = nullptr;
        bool is_service = false;
        const auto *entry_host = core.find_host(entry->host_name());
        const auto *entry_service =
            core.find_service(entry->host_name(), entry->service_description());
        switch (entry->kind()) {
            case LogEntryKind::none:
            case LogEntryKind::core_starting:
            case LogEntryKind::core_stopping:
            case LogEntryKind::log_version:
            case LogEntryKind::acknowledge_alert_host:
            case LogEntryKind::acknowledge_alert_service:
                break;
            case LogEntryKind::alert_service:
            case LogEntryKind::state_service:
            case LogEntryKind::state_service_initial:
            case LogEntryKind::downtime_alert_service:
            case LogEntryKind::flapping_service:
                key = entry_service != nullptr
                          ? entry_service->handleForStateHistory()
                          : nullptr;
                is_service = true;
            // fall-through
            case LogEntryKind::alert_host:
            case LogEntryKind::state_host:
            case LogEntryKind::state_host_initial:
            case LogEntryKind::downtime_alert_host:
            case LogEntryKind::flapping_host: {
                if (!is_service) {
                    key = entry_host == nullptr
                              ? nullptr
                              : entry_host->handleForStateHistory();
                }

                if (key == nullptr) {
                    continue;
                }

                if (object_blacklist.contains(key)) {
                    // Host/Service is not needed for this query and has already
                    // been filtered out.
                    continue;
                }

                // Find state object for this host/service
                HostServiceState *state = nullptr;
                auto it_hst = state_info.find(key);
                if (it_hst == state_info.end()) {
                    // Create state object that we also need for filtering right
                    // now
                    state = new HostServiceState();
                    state->_is_host = entry->service_description().empty();
                    state->_host = entry_host;
                    state->_service = entry_service;
                    state->_host_name = entry->host_name();
                    state->_service_description = entry->service_description();

                    // No state found. Now check if this host/services is
                    // filtered out.  Note: we currently do not filter out hosts
                    // since they might be needed for service states
                    if (!entry->service_description().empty()) {
                        if (!object_filter->accepts(Row{state}, user,
                                                    query.timezoneOffset())) {
                            object_blacklist.insert(key);
                            delete state;
                            continue;
                        }
                    }

                    // Host/Service relations
                    if (state->_is_host) {
                        for (const auto &[key, hst] : state_info) {
                            if (hst->_host != nullptr &&
                                hst->_host->handleForStateHistory() ==
                                    state->_host->handleForStateHistory()) {
                                state->_services.push_back(hst);
                            }
                        }
                    } else {
                        auto it_inh = state_info.find(
                            state->_host->handleForStateHistory());
                        if (it_inh != state_info.end()) {
                            it_inh->second->_services.push_back(state);
                        }
                    }
                    // Store this state object for tracking state transitions
                    state_info.emplace(key, state);
                    state->_from = since;

                    // Get notification period of host/service
                    // If this host/service is no longer available in nagios ->
                    // set to ""
                    state->_notification_period =
                        state->_service != nullptr
                            ? state->_service->notificationPeriodName()
                        : state->_host != nullptr
                            ? state->_host->notificationPeriodName()
                            : "";

                    // Same for service period.
                    state->_service_period =
                        state->_service != nullptr
                            ? state->_service->servicePeriodName()
                        : state->_host != nullptr
                            ? state->_host->servicePeriodName()
                            : "";

                    // Determine initial in_notification_period status
                    auto tmp_period =
                        notification_periods.find(state->_notification_period);
                    if (tmp_period != notification_periods.end()) {
                        state->_in_notification_period = tmp_period->second;
                    } else {
                        state->_in_notification_period = 1;
                    }

                    // Same for service period
                    tmp_period =
                        notification_periods.find(state->_service_period);
                    if (tmp_period != notification_periods.end()) {
                        state->_in_service_period = tmp_period->second;
                    } else {
                        state->_in_service_period = 1;
                    }

                    // If this key is a service try to find its host and apply
                    // its _in_host_downtime and _host_down parameters
                    if (!state->_is_host) {
                        auto my_host = state_info.find(
                            state->_host->handleForStateHistory());
                        if (my_host != state_info.end()) {
                            state->_in_host_downtime =
                                my_host->second->_in_host_downtime;
                            state->_host_down = my_host->second->_host_down;
                        }
                    }

                    // Log UNMONITORED state if this host or service just
                    // appeared within the query timeframe
                    // It gets a grace period of ten minutes (nagios startup)
                    if (!only_update && entry->time() - since > 10min) {
                        state->_debug_info = "UNMONITORED ";
                        state->_state = -1;
                    }
                } else {
                    state = it_hst->second;
                }

                auto state_changed = updateHostServiceState(
                    query, user, core, query_timeframe, entry, state,
                    only_update, notification_periods);
                // Host downtime or state changes also affect its services
                if (entry->kind() == LogEntryKind::alert_host ||
                    entry->kind() == LogEntryKind::state_host ||
                    entry->kind() == LogEntryKind::downtime_alert_host) {
                    if (state_changed == ModificationStatus::changed) {
                        for (auto &svc : state->_services) {
                            updateHostServiceState(
                                query, user, core, query_timeframe, entry, svc,
                                only_update, notification_periods);
                        }
                    }
                }
                break;
            }
            case LogEntryKind::timeperiod_transition: {
                try {
                    const TimeperiodTransition tpt(entry->options());
                    notification_periods[tpt.name()] = tpt.to();
                    for (const auto &[key, hst] : state_info) {
                        updateHostServiceState(
                            query, user, core, query_timeframe, entry, hst,
                            only_update, notification_periods);
                    }
                } catch (const std::logic_error &e) {
                    Warning(core.loggerLivestatus())
                        << "Error: Invalid syntax of TIMEPERIOD TRANSITION: "
                        << entry->message();
                }
                break;
            }
            case LogEntryKind::log_initial_states: {
                // This feature is only available if log_initial_states is set
                // to 1. If log_initial_states is set, each nagios startup logs
                // the initial states of all known hosts and services. Therefore
                // we can detect if a host is no longer available after a nagios
                // startup. If it still exists an INITIAL HOST/SERVICE state
                // entry will follow up shortly.
                for (const auto &[key, hst] : state_info) {
                    if (!hst->_has_vanished) {
                        hst->_last_known_time = entry->time();
                        hst->_may_no_longer_exist = true;
                    }
                }
                in_nagios_initial_states = true;
                break;
            }
        }
    }

    // Create final reports
    if (!abort_query_) {
        for (const auto &[key, hst] : state_info) {
            // No trace since the last two nagios startup -> host/service has
            // vanished
            if (hst->_may_no_longer_exist) {
                // Log last known state up to nagios restart
                hst->_time = hst->_last_known_time;
                hst->_until = hst->_last_known_time;
                process(query, user, query_timeframe, hst);

                // Set absent state
                hst->_state = -1;
                hst->_debug_info = "UNMONITORED";
                hst->_log_output = "";
                hst->_long_log_output = "";
            }

            hst->_time = until - 1s;
            hst->_until = hst->_time;

            process(query, user, query_timeframe, hst);
        }
    }

    for (auto &[key, hst] : state_info) {
        delete hst;
    }
}

TableStateHistory::ModificationStatus TableStateHistory::updateHostServiceState(
    Query &query, const User &user, const ICore &core,
    std::chrono::system_clock::duration query_timeframe, const LogEntry *entry,
    HostServiceState *hss, bool only_update,
    const std::map<std::string, int> &notification_periods) {
    ModificationStatus state_changed{ModificationStatus::changed};

    // Revive host / service if it was unmonitored
    if (entry->kind() != LogEntryKind::timeperiod_transition &&
        hss->_has_vanished) {
        hss->_time = hss->_last_known_time;
        hss->_until = hss->_last_known_time;
        if (!only_update) {
            process(query, user, query_timeframe, hss);
        }

        hss->_may_no_longer_exist = false;
        hss->_has_vanished = false;
        // Set absent state
        hss->_state = -1;
        hss->_debug_info = "UNMONITORED";
        hss->_in_downtime = 0;
        hss->_in_notification_period = 0;
        hss->_in_service_period = 0;
        hss->_is_flapping = 0;
        hss->_log_output = "";
        hss->_long_log_output = "";

        // Apply latest notification period information and set the host_state
        // to unmonitored
        auto it_status = notification_periods.find(hss->_notification_period);
        if (it_status != notification_periods.end()) {
            hss->_in_notification_period = it_status->second;
        } else {
            // No notification period information available -> within
            // notification period
            hss->_in_notification_period = 1;
        }

        // Same for service period
        it_status = notification_periods.find(hss->_service_period);
        if (it_status != notification_periods.end()) {
            hss->_in_service_period = it_status->second;
        } else {
            // No service period information available -> within service period
            hss->_in_service_period = 1;
        }
    }

    // Update basic information
    hss->_time = entry->time();
    hss->_lineno = entry->lineno();
    hss->_until = entry->time();

    // A timeperiod entry never brings an absent host or service into
    // existence..
    if (entry->kind() != LogEntryKind::timeperiod_transition) {
        hss->_may_no_longer_exist = false;
    }

    switch (entry->kind()) {
        case LogEntryKind::none:
        case LogEntryKind::core_starting:
        case LogEntryKind::core_stopping:
        case LogEntryKind::log_version:
        case LogEntryKind::log_initial_states:
        case LogEntryKind::acknowledge_alert_host:
        case LogEntryKind::acknowledge_alert_service:
            break;
        case LogEntryKind::state_host:
        case LogEntryKind::state_host_initial:
        case LogEntryKind::alert_host: {
            if (hss->_is_host) {
                if (hss->_state != entry->state()) {
                    if (!only_update) {
                        process(query, user, query_timeframe, hss);
                    }
                    hss->_state = entry->state();
                    hss->_host_down = static_cast<int>(entry->state() > 0);
                    hss->_debug_info = "HOST STATE";
                } else {
                    state_changed = ModificationStatus::unchanged;
                }
            } else if (hss->_host_down !=
                       static_cast<int>(entry->state() > 0)) {
                if (!only_update) {
                    process(query, user, query_timeframe, hss);
                }
                hss->_host_down = static_cast<int>(entry->state() > 0);
                hss->_debug_info = "SVC HOST STATE";
            }
            break;
        }
        case LogEntryKind::state_service:
        case LogEntryKind::state_service_initial:
        case LogEntryKind::alert_service: {
            if (hss->_state != entry->state()) {
                if (!only_update) {
                    process(query, user, query_timeframe, hss);
                }
                hss->_debug_info = "SVC ALERT";
                hss->_state = entry->state();
            }
            break;
        }
        case LogEntryKind::downtime_alert_host: {
            const int downtime_active =
                entry->state_type().starts_with("STARTED") ? 1 : 0;

            if (hss->_in_host_downtime != downtime_active) {
                if (!only_update) {
                    process(query, user, query_timeframe, hss);
                }
                hss->_debug_info =
                    hss->_is_host ? "HOST DOWNTIME" : "SVC HOST DOWNTIME";
                hss->_in_host_downtime = downtime_active;
                if (hss->_is_host) {
                    hss->_in_downtime = downtime_active;
                }
            } else {
                state_changed = ModificationStatus::unchanged;
            }
            break;
        }
        case LogEntryKind::downtime_alert_service: {
            const int downtime_active =
                entry->state_type().starts_with("STARTED") ? 1 : 0;
            if (hss->_in_downtime != downtime_active) {
                if (!only_update) {
                    process(query, user, query_timeframe, hss);
                }
                hss->_debug_info = "DOWNTIME SERVICE";
                hss->_in_downtime = downtime_active;
            }
            break;
        }
        case LogEntryKind::flapping_host:
        case LogEntryKind::flapping_service: {
            const int flapping_active =
                entry->state_type().starts_with("STARTED") ? 1 : 0;
            if (hss->_is_flapping != flapping_active) {
                if (!only_update) {
                    process(query, user, query_timeframe, hss);
                }
                hss->_debug_info = "FLAPPING ";
                hss->_is_flapping = flapping_active;
            } else {
                state_changed = ModificationStatus::unchanged;
            }
            break;
        }
        case LogEntryKind::timeperiod_transition: {
            try {
                const TimeperiodTransition tpt(entry->options());
                // if no _host pointer is available the initial status of
                // _in_notification_period (1) never changes
                if (hss->_host != nullptr &&
                    tpt.name() == hss->_notification_period) {
                    if (tpt.to() != hss->_in_notification_period) {
                        if (!only_update) {
                            process(query, user, query_timeframe, hss);
                        }
                        hss->_debug_info = "TIMEPERIOD ";
                        hss->_in_notification_period = tpt.to();
                    }
                }
                // same for service period
                if (hss->_host != nullptr &&
                    tpt.name() == hss->_service_period) {
                    if (tpt.to() != hss->_in_service_period) {
                        if (!only_update) {
                            process(query, user, query_timeframe, hss);
                        }
                        hss->_debug_info = "TIMEPERIOD ";
                        hss->_in_service_period = tpt.to();
                    }
                }
            } catch (const std::logic_error &e) {
                Warning(core.loggerLivestatus())
                    << "Error: Invalid syntax of TIMEPERIOD TRANSITION: "
                    << entry->message();
            }
            break;
        }
    }

    if (entry->kind() != LogEntryKind::timeperiod_transition) {
        const bool fix_me =
            (entry->kind() == LogEntryKind::state_host_initial ||
             entry->kind() == LogEntryKind::state_service_initial) &&
            entry->plugin_output() == "(null)";
        hss->_log_output = fix_me ? "" : entry->plugin_output();
        hss->_long_log_output = entry->long_plugin_output();
    }

    return state_changed;
}

void TableStateHistory::process(
    Query &query, const User &user,
    std::chrono::system_clock::duration query_timeframe,
    HostServiceState *hss) {
    hss->_duration = hss->_until - hss->_from;
    hss->computePerStateDurations(query_timeframe);

    // if (hss->_duration > 0)
    abort_query_ =
        user.is_authorized_for_object(hss->_host, hss->_service, false) &&
        !query.processDataset(Row{hss});

    hss->_from = hss->_until;
}

std::shared_ptr<Column> TableStateHistory::column(std::string colname) const {
    try {
        // First try to find column in the usual way
        return Table::column(colname);
    } catch (const std::runtime_error &e) {
        // Now try with prefix "current_", since our joined tables have this
        // prefix in order to make clear that we access current and not historic
        // data and in order to prevent mixing up historic and current fields
        // with the same name.
        return Table::column("current_" + colname);
    }
}
