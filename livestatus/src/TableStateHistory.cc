// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableStateHistory.h"

#include <chrono>
#include <cstdint>
#include <ctime>
#include <memory>
#include <mutex>
#include <optional>
#include <ostream>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

#include "Column.h"
#include "DoubleLambdaColumn.h"
#include "Filter.h"
#include "HostServiceState.h"
#include "IntLambdaColumn.h"
#include "LogEntry.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "StringLambdaColumn.h"
#include "StringUtils.h"
#include "TableHosts.h"
#include "TableServices.h"
#include "TimeLambdaColumn.h"

#ifdef CMC
// This seems to be an IWYU bug: If we remove the includes as suggested, we
// would do a member access on an incomplete type.
#include "Host.h"     // IWYU pragma: keep
#include "Service.h"  // IWYU pragma: keep
#include "Timeperiod.h"
// NOLINTNEXTLINE(cppcoreguidelines-macro-usage)
#define STATE_OK 0
// NOLINTNEXTLINE(cppcoreguidelines-macro-usage)
#define STATE_WARNING 1
// NOLINTNEXTLINE(cppcoreguidelines-macro-usage)
#define STATE_CRITICAL 2
// NOLINTNEXTLINE(cppcoreguidelines-macro-usage)
#define STATE_UNKNOWN 3
#else
#include <unordered_map>

#include "auth.h"
#include "nagios.h"
#endif

namespace {
constexpr unsigned classmask_statehist =
    (1U << static_cast<int>(LogEntry::Class::alert)) |    //
    (1U << static_cast<int>(LogEntry::Class::program)) |  //
    (1U << static_cast<int>(LogEntry::Class::state)) |    //
    (1U << static_cast<int>(LogEntry::Class::text));
}  // namespace

#ifndef CMC
namespace {
std::string getCustomVariable(const MonitoringCore *mc,
                              customvariablesmember *const *cvm,
                              const std::string &name) {
    auto attrs = mc->customAttributes(cvm, AttributeKind::custom_variables);
    auto it = attrs.find(name);
    return it == attrs.end() ? "" : it->second;
}
}  // namespace
#endif

TableStateHistory::TableStateHistory(MonitoringCore *mc, LogCache *log_cache)
    : Table(mc), _log_cache(log_cache) {
    ColumnOffsets offsets{};
    addColumn(std::make_unique<TimeLambdaColumn<HostServiceState>>(
        "time", "Time of the log event (seconds since 1/1/1970)", offsets,
        [](const HostServiceState &r) {
            return std::chrono::system_clock::from_time_t(r._time);
        }));
    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "lineno", "The number of the line in the log file", offsets,
        [](const HostServiceState &r) { return r._lineno; }));
    addColumn(std::make_unique<TimeLambdaColumn<HostServiceState>>(
        "from", "Start time of state (seconds since 1/1/1970)", offsets,
        [](const HostServiceState &r) {
            return std::chrono::system_clock::from_time_t(r._from);
        }));
    addColumn(std::make_unique<TimeLambdaColumn<HostServiceState>>(
        "until", "End time of state (seconds since 1/1/1970)", offsets,
        [](const HostServiceState &r) {
            return std::chrono::system_clock::from_time_t(r._until);
        }));
    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "duration", "Duration of state (until - from)", offsets,
        [](const HostServiceState &r) { return r._duration; }));
    addColumn(std::make_unique<DoubleLambdaColumn<HostServiceState>>(
        "duration_part", "Duration part in regard to the query timeframe",
        offsets, [](const HostServiceState &r) { return r._duration_part; }));
    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "state",
        "The state of the host or service in question - OK(0) / WARNING(1) / CRITICAL(2) / UNKNOWN(3) / UNMONITORED(-1)",
        offsets, [](const HostServiceState &r) { return r._state; }));
    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "host_down", "Shows if the host of this service is down", offsets,
        [](const HostServiceState &r) { return r._host_down; }));
    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "in_downtime", "Shows if the host or service is in downtime", offsets,
        [](const HostServiceState &r) { return r._in_downtime; }));
    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "in_host_downtime", "Shows if the host of this service is in downtime",
        offsets,
        [](const HostServiceState &r) { return r._in_host_downtime; }));
    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "is_flapping", "Shows if the host or service is flapping", offsets,
        [](const HostServiceState &r) { return r._is_flapping; }));
    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "in_notification_period",
        "Shows if the host or service is within its notification period",
        offsets,
        [](const HostServiceState &r) { return r._in_notification_period; }));
    addColumn(std::make_unique<StringLambdaColumn<HostServiceState>>(
        "notification_period",
        "The notification period of the host or service in question", offsets,
        [](const HostServiceState &r) { return r._notification_period; }));
    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "in_service_period",
        "Shows if the host or service is within its service period", offsets,
        [](const HostServiceState &r) { return r._in_service_period; }));
    addColumn(std::make_unique<StringLambdaColumn<HostServiceState>>(
        "service_period",
        "The service period of the host or service in question", offsets,
        [](const HostServiceState &r) { return r._service_period; }));
    addColumn(std::make_unique<StringLambdaColumn<HostServiceState>>(
        "debug_info", "Debug information", offsets,
        [](const HostServiceState &r) { return r._debug_info; }));
    addColumn(std::make_unique<StringLambdaColumn<HostServiceState>>(
        "host_name", "Host name", offsets,
        [](const HostServiceState &r) { return r._host_name; }));
    addColumn(std::make_unique<StringLambdaColumn<HostServiceState>>(
        "service_description", "Description of the service", offsets,
        [](const HostServiceState &r) { return r._service_description; }));
    addColumn(std::make_unique<StringLambdaColumn<HostServiceState>>(
        "log_output", "Logfile output relevant for this state", offsets,
        [](const HostServiceState &r) { return r._log_output; }));
    addColumn(std::make_unique<StringLambdaColumn<HostServiceState>>(
        "long_log_output", "Complete logfile output relevant for this state",
        offsets, [](const HostServiceState &r) { return r._long_log_output; }));

    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "duration_ok", "OK duration of state ( until - from )", offsets,
        [](const HostServiceState &r) { return r._duration_ok; }));
    addColumn(std::make_unique<DoubleLambdaColumn<HostServiceState>>(
        "duration_part_ok", "OK duration part in regard to the query timeframe",
        offsets,
        [](const HostServiceState &r) { return r._duration_part_ok; }));

    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "duration_warning", "WARNING duration of state (until - from)", offsets,
        [](const HostServiceState &r) { return r._duration_warning; }));
    addColumn(std::make_unique<DoubleLambdaColumn<HostServiceState>>(
        "duration_part_warning",
        "WARNING duration part in regard to the query timeframe", offsets,
        [](const HostServiceState &r) { return r._duration_part_warning; }));

    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "duration_critical", "CRITICAL duration of state (until - from)",
        offsets,
        [](const HostServiceState &r) { return r._duration_critical; }));
    addColumn(std::make_unique<DoubleLambdaColumn<HostServiceState>>(
        "duration_part_critical",
        "CRITICAL duration part in regard to the query timeframe", offsets,
        [](const HostServiceState &r) { return r._duration_part_critical; }));

    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "duration_unknown", "UNKNOWN duration of state (until - from)", offsets,
        [](const HostServiceState &r) { return r._duration_unknown; }));
    addColumn(std::make_unique<DoubleLambdaColumn<HostServiceState>>(
        "duration_part_unknown",
        "UNKNOWN duration part in regard to the query timeframe", offsets,
        [](const HostServiceState &r) { return r._duration_part_unknown; }));

    addColumn(std::make_unique<IntLambdaColumn<HostServiceState>>(
        "duration_unmonitored", "UNMONITORED duration of state (until - from)",
        offsets,
        [](const HostServiceState &r) { return r._duration_unmonitored; }));
    addColumn(std::make_unique<DoubleLambdaColumn<HostServiceState>>(
        "duration_part_unmonitored",
        "UNMONITORED duration part in regard to the query timeframe", offsets,
        [](const HostServiceState &r) {
            return r._duration_part_unmonitored;
        }));

    // join host and service tables
    TableHosts::addColumns(this, "current_host_", offsets.add([](Row r) {
        return r.rawData<HostServiceState>()->_host;
    }));
    TableServices::addColumns(this, "current_service_", offsets.add([](Row r) {
        return r.rawData<HostServiceState>()->_service;
    }),
                              false /* no hosts table */);
}

std::string TableStateHistory::name() const { return "statehist"; }

std::string TableStateHistory::namePrefix() const { return "statehist_"; }

void TableStateHistory::getPreviousLogentry() {
    while (_it_entries == _entries->begin()) {
        // open previous logfile
        if (_it_logs == _log_cache->begin()) {
            return;
        }
        --_it_logs;
        _entries = _it_logs->second->getEntriesFor(core()->maxLinesPerLogFile(),
                                                   classmask_statehist);
        _it_entries = _entries->end();
    }
    --_it_entries;
}

LogEntry *TableStateHistory::getNextLogentry() {
    if (_it_entries != _entries->end()) {
        ++_it_entries;
    }

    while (_it_entries == _entries->end()) {
        auto it_logs_cpy = _it_logs;
        if (++it_logs_cpy == _log_cache->end()) {
            return nullptr;
        }
        ++_it_logs;
        _entries = _it_logs->second->getEntriesFor(core()->maxLinesPerLogFile(),
                                                   classmask_statehist);
        _it_entries = _entries->begin();
    }
    return _it_entries->second.get();
}

namespace {
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
    return query.partialFilter(
        "current host/service columns", [](const Column &column) {
            return mk::starts_with(column.name(), "current_") ||
                   mk::starts_with(column.name(), "host_") ||
                   mk::starts_with(column.name(), "service_");
        });
}

void TableStateHistory::answerQuery(Query *query) {
    auto object_filter = createPartialFilter(*query);
    std::lock_guard<std::mutex> lg(_log_cache->_lock);
    _log_cache->update();
    if (_log_cache->begin() == _log_cache->end()) {
        return;
    }

    // This flag might be set to true by the return value of processDataset(...)
    _abort_query = false;

    // Keep track of the historic state of services/hosts here
    std::map<HostServiceKey, HostServiceState *> state_info;

    // Store hosts/services that we have filtered out here
    std::set<HostServiceKey> object_blacklist;

    // Optimize time interval for the query. In log querys there should always
    // be a time range in form of one or two filter expressions over time. We
    // use that to limit the number of logfiles we need to scan and to find the
    // optimal entry point into the logfile
    if (auto glb = query->greatestLowerBoundFor("time")) {
        _since = *glb;
    } else {
        query->invalidRequest(
            "Start of timeframe required. e.g. Filter: time > 1234567890");
        return;
    }
    _until = query->leastUpperBoundFor("time").value_or(time(nullptr)) + 1;

    _query_timeframe = _until - _since - 1;
    if (_query_timeframe == 0) {
        query->invalidRequest("Query timeframe is 0 seconds");
        return;
    }

    // Switch to last logfile (we have at least one)
    _it_logs = _log_cache->end();
    --_it_logs;
    auto newest_log = _it_logs;

    // Now find the log where 'since' starts.
    while (_it_logs != _log_cache->begin() && _it_logs->first >= _since) {
        --_it_logs;  // go back in history
    }

    // Check if 'until' is within these logfiles
    if (_it_logs->first > _until) {
        // All logfiles are too new, invalid timeframe
        // -> No data available. Return empty result.
        return;
    }

    // Determine initial logentry
    _entries = _it_logs->second->getEntriesFor(core()->maxLinesPerLogFile(),
                                               classmask_statehist);
    if (!_entries->empty() && _it_logs != newest_log) {
        _it_entries = _entries->end();
        // Check last entry. If it's younger than _since -> use this logfile too
        if (--_it_entries != _entries->begin()) {
            if (_it_entries->second->_time >= _since) {
                _it_entries = _entries->begin();
            }
        }
    } else {
        _it_entries = _entries->begin();
    }

    // From now on use getPreviousLogentry() / getNextLogentry()
    bool only_update = true;
    bool in_nagios_initial_states = false;

    while (LogEntry *entry = getNextLogentry()) {
        if (_abort_query) {
            break;
        }

        if (entry->_time >= _until) {
            getPreviousLogentry();
            break;
        }
        if (only_update && entry->_time >= _since) {
            // Reached start of query timeframe. From now on let's produce real
            // output. Update _from time of every state entry
            for (auto &it_hst : state_info) {
                it_hst.second->_from = _since;
                it_hst.second->_until = _since;
            }
            only_update = false;
        }

        if (in_nagios_initial_states &&
            !(entry->_kind == LogEntryKind::state_service_initial ||
              entry->_kind == LogEntryKind::state_host_initial)) {
            // Set still unknown hosts / services to unmonitored
            for (auto &it_hst : state_info) {
                HostServiceState *hst = it_hst.second;
                if (hst->_may_no_longer_exist) {
                    hst->_has_vanished = true;
                }
            }
            in_nagios_initial_states = false;
        }

        HostServiceKey key = nullptr;
        bool is_service = false;
        // TODO(sp): Remove ugly casts.
        auto *entry_host =
            reinterpret_cast<host *>(core()->find_host(entry->_host_name));
        auto *entry_service = reinterpret_cast<service *>(core()->find_service(
            entry->_host_name, entry->_service_description));
        switch (entry->_kind) {
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
                key = entry_service;
                is_service = true;
            // fall-through
            case LogEntryKind::alert_host:
            case LogEntryKind::state_host:
            case LogEntryKind::state_host_initial:
            case LogEntryKind::downtime_alert_host:
            case LogEntryKind::flapping_host: {
                if (!is_service) {
                    key = entry_host;
                }

                if (key == nullptr) {
                    continue;
                }

                if (object_blacklist.find(key) != object_blacklist.end()) {
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
                    state->_is_host = entry->_service_description.empty();
                    state->_host = entry_host;
                    state->_service = entry_service;
                    state->_host_name = entry->_host_name;
                    state->_service_description = entry->_service_description;

                    // No state found. Now check if this host/services is
                    // filtered out.  Note: we currently do not filter out hosts
                    // since they might be needed for service states
                    if (!entry->_service_description.empty()) {
                        if (!object_filter->accepts(Row(state),
                                                    query->authUser(),
                                                    query->timezoneOffset())) {
                            object_blacklist.insert(key);
                            delete state;
                            continue;
                        }
                    }

                    // Host/Service relations
                    if (state->_is_host) {
                        for (auto &it_inh : state_info) {
                            if (it_inh.second->_host == state->_host) {
                                state->_services.push_back(it_inh.second);
                            }
                        }
                    } else {
                        auto it_inh = state_info.find(state->_host);
                        if (it_inh != state_info.end()) {
                            it_inh->second->_services.push_back(state);
                        }
                    }

                    // Store this state object for tracking state transitions
                    state_info.emplace(key, state);
                    state->_from = _since;

                    // Get notification period of host/service
                    // If this host/service is no longer availabe in nagios ->
                    // set to ""
                    if (state->_service != nullptr) {
#ifdef CMC
                        state->_notification_period =
                            state->_service->notificationPeriod()->name();
#else
                        const auto *np = state->_service->notification_period;
                        state->_notification_period = np == nullptr ? "" : np;
#endif
                    } else if (state->_host != nullptr) {
#ifdef CMC
                        state->_notification_period =
                            state->_host->notificationPeriod()->name();
#else
                        const auto *np = state->_host->notification_period;
                        state->_notification_period = np == nullptr ? "" : np;
#endif
                    } else {
                        state->_notification_period = "";
                    }

                    // Same for service period. For Nagios this is a bit
                    // different, since this is no native field but just a
                    // custom variable
                    if (state->_service != nullptr) {
#ifdef CMC
                        state->_service_period =
                            state->_service->servicePeriod()->name();
#else
                        state->_service_period = getCustomVariable(
                            core(), &state->_service->custom_variables,
                            "SERVICE_PERIOD");
#endif
                    } else if (state->_host != nullptr) {
#ifdef CMC
                        state->_service_period =
                            state->_host->servicePeriod()->name();
#else
                        state->_service_period = getCustomVariable(
                            core(), &state->_host->custom_variables,
                            "SERVICE_PERIOD");
#endif
                    } else {
                        state->_service_period = "";
                    }

                    // Determine initial in_notification_period status
                    auto tmp_period =
                        _notification_periods.find(state->_notification_period);
                    if (tmp_period != _notification_periods.end()) {
                        state->_in_notification_period = tmp_period->second;
                    } else {
                        state->_in_notification_period = 1;
                    }

                    // Same for service period
                    tmp_period =
                        _notification_periods.find(state->_service_period);
                    if (tmp_period != _notification_periods.end()) {
                        state->_in_service_period = tmp_period->second;
                    } else {
                        state->_in_service_period = 1;
                    }

                    // If this key is a service try to find its host and apply
                    // its _in_host_downtime and _host_down parameters
                    if (!state->_is_host) {
                        auto my_host = state_info.find(state->_host);
                        if (my_host != state_info.end()) {
                            state->_in_host_downtime =
                                my_host->second->_in_host_downtime;
                            state->_host_down = my_host->second->_host_down;
                        }
                    }

                    // Log UNMONITORED state if this host or service just
                    // appeared within the query timeframe
                    // It gets a grace period of ten minutes (nagios startup)
                    if (!only_update && entry->_time - _since > 60 * 10) {
                        state->_debug_info = "UNMONITORED ";
                        state->_state = -1;
                    }
                } else {
                    state = it_hst->second;
                }

                int state_changed =
                    updateHostServiceState(query, entry, state, only_update);
                // Host downtime or state changes also affect its services
                if (entry->_kind == LogEntryKind::alert_host ||
                    entry->_kind == LogEntryKind::state_host ||
                    entry->_kind == LogEntryKind::downtime_alert_host) {
                    if (state_changed != 0) {
                        for (auto &svc : state->_services) {
                            updateHostServiceState(query, entry, svc,
                                                   only_update);
                        }
                    }
                }
                break;
            }
            case LogEntryKind::timeperiod_transition: {
                try {
                    TimeperiodTransition tpt(entry->_options);
                    _notification_periods[tpt.name()] = tpt.to();
                    for (auto &it_hst : state_info) {
                        updateHostServiceState(query, entry, it_hst.second,
                                               only_update);
                    }
                } catch (const std::logic_error &e) {
                    Warning(logger())
                        << "Error: Invalid syntax of TIMEPERIOD TRANSITION: "
                        << entry->_message;
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
                for (auto &it_hst : state_info) {
                    if (!it_hst.second->_has_vanished) {
                        it_hst.second->_last_known_time = entry->_time;
                        it_hst.second->_may_no_longer_exist = true;
                    }
                }
                in_nagios_initial_states = true;
                break;
            }
        }
    }

    // Create final reports
    auto it_hst = state_info.begin();
    if (!_abort_query) {
        while (it_hst != state_info.end()) {
            HostServiceState *hst = it_hst->second;

            // No trace since the last two nagios startup -> host/service has
            // vanished
            if (hst->_may_no_longer_exist) {
                // Log last known state up to nagios restart
                hst->_time = hst->_last_known_time;
                hst->_until = hst->_last_known_time;
                process(query, hst);

                // Set absent state
                hst->_state = -1;
                hst->_debug_info = "UNMONITORED";
                hst->_log_output = "";
                hst->_long_log_output = "";
            }

            hst->_time = _until - 1;
            hst->_until = hst->_time;

            process(query, hst);
            ++it_hst;
        }
    }

    // Cleanup !
    it_hst = state_info.begin();
    while (it_hst != state_info.end()) {
        delete it_hst->second;
        ++it_hst;
    }
    state_info.clear();
    object_blacklist.clear();
}

int TableStateHistory::updateHostServiceState(Query *query,
                                              const LogEntry *entry,
                                              HostServiceState *hs_state,
                                              bool only_update) {
    int state_changed = 1;

    // Revive host / service if it was unmonitored
    if (entry->_kind != LogEntryKind::timeperiod_transition &&
        hs_state->_has_vanished) {
        hs_state->_time = hs_state->_last_known_time;
        hs_state->_until = hs_state->_last_known_time;
        if (!only_update) {
            process(query, hs_state);
        }

        hs_state->_may_no_longer_exist = false;
        hs_state->_has_vanished = false;
        // Set absent state
        hs_state->_state = -1;
        hs_state->_debug_info = "UNMONITORED";
        hs_state->_in_downtime = 0;
        hs_state->_in_notification_period = 0;
        hs_state->_in_service_period = 0;
        hs_state->_is_flapping = 0;
        hs_state->_log_output = "";
        hs_state->_long_log_output = "";

        // Apply latest notification period information and set the host_state
        // to unmonitored
        auto it_status =
            _notification_periods.find(hs_state->_notification_period);
        if (it_status != _notification_periods.end()) {
            hs_state->_in_notification_period = it_status->second;
        } else {
            // No notification period information available -> within
            // notification period
            hs_state->_in_notification_period = 1;
        }

        // Same for service period
        it_status = _notification_periods.find(hs_state->_service_period);
        if (it_status != _notification_periods.end()) {
            hs_state->_in_service_period = it_status->second;
        } else {
            // No service period information available -> within service period
            hs_state->_in_service_period = 1;
        }
    }

    // Update basic information
    hs_state->_time = entry->_time;
    hs_state->_lineno = entry->_lineno;
    hs_state->_until = entry->_time;

    // A timeperiod entry never brings an absent host or service into
    // existence..
    if (entry->_kind != LogEntryKind::timeperiod_transition) {
        hs_state->_may_no_longer_exist = false;
    }

    switch (entry->_kind) {
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
            if (hs_state->_is_host) {
                if (hs_state->_state != entry->_state) {
                    if (!only_update) {
                        process(query, hs_state);
                    }
                    hs_state->_state = entry->_state;
                    hs_state->_host_down = static_cast<int>(entry->_state > 0);
                    hs_state->_debug_info = "HOST STATE";
                } else {
                    state_changed = 0;
                }
            } else if (hs_state->_host_down !=
                       static_cast<int>(entry->_state > 0)) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_host_down = static_cast<int>(entry->_state > 0);
                hs_state->_debug_info = "SVC HOST STATE";
            }
            break;
        }
        case LogEntryKind::state_service:
        case LogEntryKind::state_service_initial:
        case LogEntryKind::alert_service: {
            if (hs_state->_state != entry->_state) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info = "SVC ALERT";
                hs_state->_state = entry->_state;
            }
            break;
        }
        case LogEntryKind::downtime_alert_host: {
            int downtime_active =
                mk::starts_with(entry->_state_type, "STARTED") ? 1 : 0;

            if (hs_state->_in_host_downtime != downtime_active) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info =
                    hs_state->_is_host ? "HOST DOWNTIME" : "SVC HOST DOWNTIME";
                hs_state->_in_host_downtime = downtime_active;
                if (hs_state->_is_host) {
                    hs_state->_in_downtime = downtime_active;
                }
            } else {
                state_changed = 0;
            }
            break;
        }
        case LogEntryKind::downtime_alert_service: {
            int downtime_active =
                mk::starts_with(entry->_state_type, "STARTED") ? 1 : 0;
            if (hs_state->_in_downtime != downtime_active) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info = "DOWNTIME SERVICE";
                hs_state->_in_downtime = downtime_active;
            }
            break;
        }
        case LogEntryKind::flapping_host:
        case LogEntryKind::flapping_service: {
            int flapping_active =
                mk::starts_with(entry->_state_type, "STARTED") ? 1 : 0;
            if (hs_state->_is_flapping != flapping_active) {
                if (!only_update) {
                    process(query, hs_state);
                }
                hs_state->_debug_info = "FLAPPING ";
                hs_state->_is_flapping = flapping_active;
            } else {
                state_changed = 0;
            }
            break;
        }
        case LogEntryKind::timeperiod_transition: {
            try {
                TimeperiodTransition tpt(entry->_options);
                // if no _host pointer is available the initial status of
                // _in_notification_period (1) never changes
                if (hs_state->_host != nullptr &&
                    tpt.name() == hs_state->_notification_period) {
                    if (tpt.to() != hs_state->_in_notification_period) {
                        if (!only_update) {
                            process(query, hs_state);
                        }
                        hs_state->_debug_info = "TIMEPERIOD ";
                        hs_state->_in_notification_period = tpt.to();
                    }
                }
                // same for service period
                if (hs_state->_host != nullptr &&
                    tpt.name() == hs_state->_service_period) {
                    if (tpt.to() != hs_state->_in_service_period) {
                        if (!only_update) {
                            process(query, hs_state);
                        }
                        hs_state->_debug_info = "TIMEPERIOD ";
                        hs_state->_in_service_period = tpt.to();
                    }
                }
            } catch (const std::logic_error &e) {
                Warning(logger())
                    << "Error: Invalid syntax of TIMEPERIOD TRANSITION: "
                    << entry->_message;
            }
            break;
        }
    }

    if (entry->_kind != LogEntryKind::timeperiod_transition) {
        bool fix_me = (entry->_kind == LogEntryKind::state_host_initial ||
                       entry->_kind == LogEntryKind::state_service_initial) &&
                      entry->_plugin_output == "(null)";
        hs_state->_log_output = fix_me ? "" : entry->_plugin_output;
        hs_state->_long_log_output = entry->_long_plugin_output;
    }

    return state_changed;
}

void TableStateHistory::process(Query *query, HostServiceState *hs_state) {
    hs_state->_duration = hs_state->_until - hs_state->_from;
    hs_state->_duration_part = static_cast<double>(hs_state->_duration) /
                               static_cast<double>(_query_timeframe);

    hs_state->_duration_unmonitored = 0;
    hs_state->_duration_part_unmonitored = 0;

    hs_state->_duration_ok = 0;
    hs_state->_duration_part_ok = 0;

    hs_state->_duration_warning = 0;
    hs_state->_duration_part_warning = 0;

    hs_state->_duration_critical = 0;
    hs_state->_duration_part_critical = 0;

    hs_state->_duration_unknown = 0;
    hs_state->_duration_part_unknown = 0;

    switch (hs_state->_state) {
        case -1:
            hs_state->_duration_unmonitored = hs_state->_duration;
            hs_state->_duration_part_unmonitored = hs_state->_duration_part;
            break;
        case STATE_OK:
            hs_state->_duration_ok = hs_state->_duration;
            hs_state->_duration_part_ok = hs_state->_duration_part;
            break;
        case STATE_WARNING:
            hs_state->_duration_warning = hs_state->_duration;
            hs_state->_duration_part_warning = hs_state->_duration_part;
            break;
        case STATE_CRITICAL:
            hs_state->_duration_critical = hs_state->_duration;
            hs_state->_duration_part_critical = hs_state->_duration_part;
            break;
        case STATE_UNKNOWN:
            hs_state->_duration_unknown = hs_state->_duration;
            hs_state->_duration_part_unknown = hs_state->_duration_part;
            break;
        default:
            break;
    }

    // if (hs_state->_duration > 0)
    HostServiceState *r = hs_state;
    _abort_query = !query->processDataset(Row(r));

    hs_state->_from = hs_state->_until;
}

bool TableStateHistory::isAuthorized(Row row, const contact *ctc) const {
    const auto *entry = rowData<HostServiceState>(row);
    service *svc = entry->_service;
    host *hst = entry->_host;
    return (hst != nullptr || svc != nullptr) &&
           is_authorized_for(core(), ctc, hst, svc);
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
