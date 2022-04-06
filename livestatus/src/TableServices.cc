// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableServices.h"

#include <algorithm>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <functional>
#include <iterator>
#include <memory>
#include <optional>
#include <sstream>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "AttributeBitmaskColumn.h"
#include "AttributeListColumn.h"
#include "BlobColumn.h"
#include "Column.h"
#include "CommentRenderer.h"
#include "CustomAttributeMap.h"
#include "DictColumn.h"
#include "DoubleColumn.h"
#include "DowntimeRenderer.h"
#include "DynamicColumn.h"
#include "DynamicRRDColumn.h"
#include "IntColumn.h"
#include "ListColumn.h"
#include "Logger.h"
#include "MacroExpander.h"
#include "Metric.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "RRDColumn.h"
#include "StringColumn.h"
#include "StringUtils.h"
#include "TableHosts.h"
#include "TimeColumn.h"
#include "TimeperiodsCache.h"
#include "auth.h"
#include "contact_fwd.h"
#include "nagios.h"
#include "pnp4nagios.h"

using namespace std::string_literals;

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern TimeperiodsCache *g_timeperiods_cache;

// TODO(ml): Here we use `static` instead of an anonymous namespace because
// of the `extern` declaration.  We should find something better.
static double staleness(const service &svc) {
    auto now =
        std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    auto check_result_age = static_cast<double>(now - svc.last_check);
    if (svc.check_interval != 0) {
        return check_result_age / (svc.check_interval * interval_length);
    }

    // check_mk PASSIVE CHECK without check interval uses the check
    // interval of its check-mk service
    bool is_cmk_passive =
        strncmp(svc.check_command_ptr->name, "check_mk-", 9) == 0;
    if (is_cmk_passive) {
        host *host = svc.host_ptr;
        for (servicesmember *svc_member = host->services; svc_member != nullptr;
             svc_member = svc_member->next) {
            service *tmp_svc = svc_member->service_ptr;
            if (strncmp(tmp_svc->check_command_ptr->name, "check-mk", 8) == 0) {
                return check_result_age / ((tmp_svc->check_interval == 0
                                                ? 1
                                                : tmp_svc->check_interval) *
                                           interval_length);
            }
        }
        // Shouldn't happen! We always expect a check-mk service
        return 1;
    }
    // Other non-cmk passive and active checks without
    // check_interval
    return check_result_age / interval_length;
}

TableServices::TableServices(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{}, true);
}

std::string TableServices::name() const { return "services"; }

std::string TableServices::namePrefix() const { return "service_"; }

// static
void TableServices::addColumns(Table *table, const std::string &prefix,
                               const ColumnOffsets &offsets, bool add_hosts) {
    auto offsets_custom_variables{offsets.add(
        [](Row r) { return &r.rawData<service>()->custom_variables; })};
    auto *mc = table->core();
    // Es fehlen noch: double-Spalten, unsigned long spalten, etliche weniger
    // wichtige Spalten und die Servicegruppen.
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "description", "Service description", offsets,
        [](const service &r) {
            return r.description == nullptr ? "" : r.description;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "display_name", "Optional display name", offsets,
        [](const service &r) {
            return r.display_name == nullptr ? "" : r.display_name;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "check_command", "Logical command name for active checks",
        offsets, [](const service &r) {
            const auto *cc = nagios_compat_service_check_command(r);
            return cc == nullptr ? "" : cc;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "check_command_expanded",
        "Logical command name for active checks, with macros expanded", offsets,
        [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(
                nagios_compat_service_check_command(r));
        }));

    table->addColumn(std::make_unique<BlobColumn<service>>(
        prefix + "robotmk_last_log", "The file content of the Robotmk log",
        offsets,
        BlobFileReader<service>{
            [mc]() { return mc->robotMkHtmlLogPath(); },
            [](const service &r) {
                return std::filesystem::path{r.host_ptr->name} / r.description /
                       "suite_last_log.html";
            }}));
    table->addColumn(std::make_unique<BlobColumn<service>>(
        prefix + "robotmk_last_log_gz",
        "The gzipped file content of the Robotmk log", offsets,
        BlobFileReader<service>{
            [mc]() { return mc->robotMkHtmlLogPath(); },
            [](const service &r) {
                return std::filesystem::path{r.host_ptr->name} / r.description /
                       "suite_last_log.html.gz";
            }}));
    table->addColumn(std::make_unique<BlobColumn<service>>(
        prefix + "robotmk_last_error_log",
        "The file content of the Robotmk error log", offsets,
        BlobFileReader<service>{
            [mc]() { return mc->robotMkHtmlLogPath(); },
            [](const service &r) {
                return std::filesystem::path{r.host_ptr->name} / r.description /
                       "suite_last_error_log.html";
            }}));
    table->addColumn(std::make_unique<BlobColumn<service>>(
        prefix + "robotmk_last_error_log_gz",
        "The gzipped file content of the Robotmk error log", offsets,
        BlobFileReader<service>{
            [mc]() { return mc->robotMkHtmlLogPath(); },
            [](const service &r) {
                return std::filesystem::path{r.host_ptr->name} / r.description /
                       "suite_last_error_log.html.gz";
            }}));

    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "event_handler", "Command used as event handler", offsets,
        [](const service &r) {
            return r.event_handler == nullptr ? "" : r.event_handler;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "plugin_output", "Output of the last check", offsets,
        [](const service &r) {
            return r.plugin_output == nullptr ? "" : r.plugin_output;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "long_plugin_output", "Long (extra) output of the last check",
        offsets, [](const service &r) {
            return r.long_plugin_output == nullptr ? "" : r.long_plugin_output;
        }));
    table->addColumn(std::make_unique<StringColumnPerfData<service>>(
        prefix + "perf_data", "Optional performance data of the last check",
        offsets, [](const service &r) {
            return r.perf_data == nullptr ? "" : r.perf_data;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "notification_period",
        "Time period in which problems of this object will be notified. If empty then notification will be always",
        offsets, [](const service &r) {
            return r.notification_period == nullptr ? ""
                                                    : r.notification_period;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "check_period",
        "Time period in which this object will be checked. If empty then the check will always be executed.",
        offsets, [](const service &r) {
            return r.check_period == nullptr ? "" : r.check_period;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "service_period",
        "Time period during which the object is expected to be available",
        offsets_custom_variables, [mc](const service &p) {
            auto attrs =
                mc->customAttributes(&p, AttributeKind::custom_variables);
            auto it = attrs.find("SERVICE_PERIOD");
            if (it != attrs.end()) {
                return it->second;
            }
            return ""s;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "notes",
        "Optional notes for this object, with macros not expanded", offsets,
        [](const service &r) { return r.notes == nullptr ? "" : r.notes; }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "notes_expanded",
        "The same as notes, but with the most important macros expanded",
        offsets, [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(r.notes);
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "notes_url",
        "An optional URL with further information about the object", offsets,
        [](const service &r) {
            return r.notes_url == nullptr ? "" : r.notes_url;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "notes_url_expanded",
        "Same es notes_url, but with the most important macros expanded",
        offsets, [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(r.notes_url);
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "action_url",
        "An optional URL to custom actions or information about this host",
        offsets, [](const service &r) {
            return r.action_url == nullptr ? "" : r.action_url;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "action_url_expanded",
        "The same as action_url, but with the most important macros expanded",
        offsets, [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(
                r.action_url);
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "icon_image",
        "The name of an image file to be used in the web pages", offsets,
        [](const service &r) {
            return r.icon_image == nullptr ? "" : r.icon_image;
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "icon_image_expanded",
        "The same as icon_image, but with the most important macros expanded",
        offsets, [mc](const service &r) {
            return ServiceMacroExpander::make(r, mc)->expandMacros(
                r.icon_image);
        }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "icon_image_alt", "Alternative text for the icon_image",
        offsets, [](const service &r) {
            return r.icon_image_alt == nullptr ? "" : r.icon_image_alt;
        }));

    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "initial_state", "Initial state", offsets,
        [](const service &r) { return r.initial_state; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "max_check_attempts",
        "Maximum attempts for active checks before a hard state", offsets,
        [](const service &r) { return r.max_attempts; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "current_attempt", "Number of the current check attempts",
        offsets, [](const service &r) { return r.current_attempt; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "state",
        "The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN",
        offsets, [](const service &r) { return r.current_state; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "has_been_checked",
        "Whether a check has already been executed (0/1)", offsets,
        [](const service &r) { return r.has_been_checked; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "last_state", "State before last state change", offsets,
        [](const service &r) { return r.last_state; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "last_hard_state", "Last hard state", offsets,
        [](const service &r) { return r.last_hard_state; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "state_type", "Type of the current state (0: soft, 1: hard)",
        offsets, [](const service &r) { return r.state_type; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "check_type", "Type of check (0: active, 1: passive)", offsets,
        [](const service &r) { return r.check_type; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "acknowledged",
        "Whether the current problem has been acknowledged (0/1)", offsets,
        [](const service &r) { return r.problem_has_been_acknowledged; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "acknowledgement_type",
        "Type of acknowledgement (0: none, 1: normal, 2: sticky)", offsets,
        [](const service &r) { return r.acknowledgement_type; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)", offsets,
        [](const service &r) { return r.no_more_notifications; }));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "last_time_ok",
        "The last time the service was OK (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_ok);
        }));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "last_time_warning",
        "The last time the service was WARN (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_warning);
        }));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "last_time_critical",
        "The last time the service was CRIT (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_critical);
        }));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "last_time_unknown",
        "The last time the service was UNKNOWN (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_unknown);
        }));

    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "last_check", "Time of the last check (Unix timestamp)",
        offsets, [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_check);
        }));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "next_check",
        "Scheduled time for the next check (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.next_check);
        }));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_notification);
        }));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)", offsets,
        [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.next_notification);
        }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "current_notification_number",
        "Number of the current notification", offsets,
        [](const service &r) { return r.current_notification_number; }));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "last_state_change",
        "Time of the last state change - soft or hard (Unix timestamp)",
        offsets, [](const service &r) {
            return std::chrono::system_clock::from_time_t(r.last_state_change);
        }));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "last_hard_state_change",
        "Time of the last hard state change - soft or hard (Unix timestamp)",
        offsets, [](const service &r) {
            return std::chrono::system_clock::from_time_t(
                r.last_hard_state_change);
        }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "scheduled_downtime_depth",
        "The number of downtimes this object is currently in", offsets,
        [](const service &r) { return r.scheduled_downtime_depth; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "is_flapping", "Whether the state is flapping (0/1)", offsets,
        [](const service &r) { return r.is_flapping; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "checks_enabled",
        "Whether checks of the object are enabled (0/1)", offsets,
        [](const service &r) { return r.checks_enabled; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)", offsets,
        [](const service &r) {
            return nagios_compat_accept_passive_service_checks(r);
        }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "event_handler_enabled",
        "Whether event handling is enabled (0/1)", offsets,
        [](const service &r) { return r.event_handler_enabled; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "notifications_enabled",
        "Whether notifications of the host are enabled (0/1)", offsets,
        [](const service &r) { return r.notifications_enabled; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled (0/1)", offsets,
        [](const service &r) { return r.process_performance_data; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "is_executing", "is there a check currently running (0/1)",
        offsets, [](const service &r) { return r.is_executing; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "active_checks_enabled",
        "Whether active checks of the object are enabled (0/1)", offsets,
        [](const service &r) { return r.checks_enabled; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness (0-2)", offsets,
        [](const service &r) { return r.check_options; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled (0/1)", offsets,
        [](const service &r) { return r.flap_detection_enabled; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "check_freshness",
        "Whether freshness checks are enabled (0/1)", offsets,
        [](const service &r) { return r.check_freshness; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "obsess_over_service",
        "The current obsess_over_service setting (0/1)", offsets,
        [](const service &r) { return nagios_compat_obsess_over_service(r); }));
    table->addColumn(std::make_unique<AttributeBitmaskColumn<service>>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified", offsets,
        [](const service &r) { return r.modified_attributes; }));
    table->addColumn(
        std::make_unique<
            AttributeListColumn<service, column::attribute_list::AttributeBit>>(
            prefix + "modified_attributes_list",
            "A list of all modified attributes", offsets, [](const service &r) {
                return column::attribute_list::encode(r.modified_attributes);
            }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "hard_state", "The effective hard state of this object",
        offsets, [](const service &svc) {
            if (svc.current_state == STATE_OK) {
                return 0;
            }
            return svc.state_type == HARD_STATE ? svc.current_state
                                                : svc.last_hard_state;
        }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this object (-1/0/1)",
        offsets, [mc](const service &svc) {
            return pnpgraph_present(mc, svc.host_ptr->name, svc.description);
        }));

    // columns of type double
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "staleness", "The staleness of this object", offsets,
        [](const service &r) { return staleness(r); }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks",
        offsets, [](const service &r) { return r.check_interval; }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a soft error",
        offsets, [](const service &r) { return r.retry_interval; }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "notification_interval",
        "Interval of periodic notification in minutes or 0 if its off", offsets,
        [](const service &r) { return r.notification_interval; }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "first_notification_delay",
        "Delay before the first notification", offsets,
        [](const service &r) { return r.first_notification_delay; }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        offsets, [](const service &r) { return r.low_flap_threshold; }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        offsets, [](const service &r) { return r.high_flap_threshold; }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        offsets, [](const service &r) { return r.latency; }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "execution_time", "Time the check needed for execution",
        offsets, [](const service &r) { return r.execution_time; }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "percent_state_change", "Percent state change", offsets,
        [](const service &r) { return r.percent_state_change; }));

    table->addColumn(std::make_unique<BoolColumn<service, true>>(
        prefix + "in_check_period",
        "Whether this object is currently in its check period (0/1)", offsets,
        [](const service &r) {
            return g_timeperiods_cache->inTimeperiod(r.check_period_ptr);
        }));
    table->addColumn(std::make_unique<BoolColumn<service, true>>(
        prefix + "in_service_period",
        "Whether this object is currently in its service period (0/1)", offsets,
        [mc](const service &r) {
            auto attrs = mc->customAttributes(&r.custom_variables,
                                              AttributeKind::custom_variables);
            auto it = attrs.find("SERVICE_PERIOD");
            return it == attrs.end() ||
                   g_timeperiods_cache->inTimeperiod(it->second);
        }));
    table->addColumn(std::make_unique<BoolColumn<service, true>>(
        prefix + "in_notification_period",
        "Whether this object is currently in its notification period (0/1)",
        offsets, [](const service &r) {
            return g_timeperiods_cache->inTimeperiod(r.notification_period_ptr);
        }));

    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "contacts", "A list of all contacts of this object", offsets,
        [](const service &r) {
            std::unordered_set<std::string> names;
            for (auto *cm = r.contacts; cm != nullptr; cm = cm->next) {
                names.insert(cm->contact_ptr->name);
            }
            for (auto *cgm = r.contact_groups; cgm != nullptr;
                 cgm = cgm->next) {
                for (auto *cm = cgm->group_ptr->members; cm != nullptr;
                     cm = cm->next) {
                    names.insert(cm->contact_ptr->name);
                }
            }
            return std::vector<std::string>(names.begin(), names.end());
        }));
    table->addColumn(std::make_unique<ListColumn<service, DowntimeData>>(
        prefix + "downtimes",
        "A list of the ids of all scheduled downtimes of this object", offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::none),
        [mc](const service &svc) {
            return mc->downtimes(
                reinterpret_cast<const MonitoringCore::Service *>(&svc));
        }));
    table->addColumn(std::make_unique<ListColumn<service, DowntimeData>>(
        prefix + "downtimes_with_info",
        "A list of the scheduled downtimes with id, author and comment",
        offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::medium),
        [mc](const service &svc) {
            return mc->downtimes(
                reinterpret_cast<const MonitoringCore::Service *>(&svc));
        }));
    table->addColumn(std::make_unique<ListColumn<service, DowntimeData>>(
        prefix + "downtimes_with_extra_info",
        "A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending",
        offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::full),
        [mc](const service &svc) {
            return mc->downtimes(
                reinterpret_cast<const MonitoringCore::Service *>(&svc));
        }));
    table->addColumn(std::make_unique<ListColumn<service, CommentData>>(
        prefix + "comments", "A list of the ids of all comments", offsets,
        std::make_unique<CommentRenderer>(CommentRenderer::verbosity::none),
        [mc](const service &svc) {
            return mc->comments(
                reinterpret_cast<const MonitoringCore::Service *>(&svc));
        }));
    table->addColumn(std::make_unique<ListColumn<service, CommentData>>(
        prefix + "comments_with_info",
        "A list of all comments with id, author and comment", offsets,
        std::make_unique<CommentRenderer>(CommentRenderer::verbosity::medium),
        [mc](const service &svc) {
            return mc->comments(
                reinterpret_cast<const MonitoringCore::Service *>(&svc));
        }));
    table->addColumn(std::make_unique<ListColumn<service, CommentData>>(
        prefix + "comments_with_extra_info",
        "A list of all comments with id, author, comment, entry type and entry time",
        offsets,
        std::make_unique<CommentRenderer>(CommentRenderer::verbosity::full),
        [mc](const service &svc) {
            return mc->comments(
                reinterpret_cast<const MonitoringCore::Service *>(&svc));
        }));

    if (add_hosts) {
        TableHosts::addColumns(table, "host_", offsets.add([](Row r) {
            return r.rawData<service>()->host_ptr;
        }));
    }

    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables", offsets,
        CustomAttributeMap::Keys{table->core(),
                                 AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables", offsets,
        CustomAttributeMap::Values{table->core(),
                                   AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<DictColumn<service>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets,
        CustomAttributeMap{table->core(), AttributeKind::custom_variables}));

    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "tag_names", "A list of the names of the tags", offsets,
        CustomAttributeMap::Keys{table->core(), AttributeKind::tags}));
    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "tag_values", "A list of the values of the tags", offsets,
        CustomAttributeMap::Values{table->core(), AttributeKind::tags}));
    table->addColumn(std::make_unique<DictColumn<service>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        CustomAttributeMap{table->core(), AttributeKind::tags}));

    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "label_names", "A list of the names of the labels", offsets,
        CustomAttributeMap::Keys{table->core(), AttributeKind::labels}));
    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "label_values", "A list of the values of the labels", offsets,
        CustomAttributeMap::Values{table->core(), AttributeKind::labels}));
    table->addColumn(std::make_unique<DictColumn<service>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        CustomAttributeMap{table->core(), AttributeKind::labels}));

    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "label_source_names",
        "A list of the names of the label sources", offsets,
        CustomAttributeMap::Keys{table->core(), AttributeKind::label_sources}));
    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "label_source_values",
        "A list of the values of the label sources", offsets,
        CustomAttributeMap::Values{table->core(),
                                   AttributeKind::label_sources}));
    table->addColumn(std::make_unique<DictColumn<service>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        CustomAttributeMap{table->core(), AttributeKind::label_sources}));

    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "groups", "A list of all service groups this object is in",
        offsets, [mc](const service &svc, const contact *auth_user) {
            User user{auth_user, mc->serviceAuthorization(),
                      mc->groupAuthorization()};
            std::vector<std::string> group_names;
            for (objectlist *list = svc.servicegroups_ptr; list != nullptr;
                 list = list->next) {
                auto *sg = static_cast<servicegroup *>(list->object_ptr);
                if (user.is_authorized_for_service_group(*sg)) {
                    group_names.emplace_back(sg->group_name);
                }
            }
            return group_names;
        }));
    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "contact_groups",
        "A list of all contact groups this object is in", offsets,
        [](const service &svc) {
            std::vector<std::string> names;
            for (const auto *cgm = svc.contact_groups; cgm != nullptr;
                 cgm = cgm->next) {
                names.emplace_back(cgm->group_ptr->group_name);
            }
            return names;
        }));

    table->addColumn(std::make_unique<ListColumn<service>>(
        prefix + "metrics",
        "A list of all metrics of this object that historically existed",
        offsets, [mc](const service &r) {
            std::vector<std::string> metrics;
            if (r.host_name == nullptr || r.description == nullptr) {
                return metrics;
            }
            auto names = scan_rrd(mc->pnpPath() / r.host_name, r.description,
                                  mc->loggerRRD());
            std::transform(std::begin(names), std::end(names),
                           std::back_inserter(metrics),
                           [](auto &&m) { return m.string(); });
            return metrics;
        }));
    table->addDynamicColumn(std::make_unique<DynamicRRDColumn<
                                ListColumn<service, RRDDataMaker::value_type>>>(
        prefix + "rrddata",
        "RRD metrics data of this object. This is a column with parameters: rrddata:COLUMN_TITLE:VARNAME:FROM_TIME:UNTIL_TIME:RESOLUTION",
        table->core(), offsets));
    table->addColumn(std::make_unique<TimeColumn<service>>(
        prefix + "cached_at",
        "For checks that base on cached agent data the time when this data was created. 0 for other services.",
        offsets, [](const service & /*r*/) {
            return std::chrono::system_clock::time_point{};
        }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "cache_interval",
        "For checks that base on cached agent data the interval in that this cache is recreated. 0 for other services.",
        offsets, [](const service & /*r*/) { return 0; }));

    table->addColumn(std::make_unique<BoolColumn<service>>(
        prefix + "in_passive_check_period",
        "Whether this service is currently in its passive check period (0/1)",
        offsets, [](const service & /*r*/) { return true; }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "passive_check_period",
        "Time period in which this (passive) service will be checked.", offsets,
        [](const service & /*r*/) { return "24X7"; }));
    table->addColumn(std::make_unique<DoubleColumn<service>>(
        prefix + "flappiness",
        "The current level of flappiness, this corresponds with the recent frequency of state changes",
        offsets, [](const service &r) { return r.percent_state_change; }));
    table->addColumn(std::make_unique<StringColumn<service>>(
        prefix + "notification_postponement_reason",
        "reason for postponing the pending notification, empty if nothing is postponed",
        offsets, [](const service & /*r*/) { return ""; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "previous_hard_state",
        "Previous hard state (that hard state before the current/last hard state)",
        offsets, [](const service & /*r*/) { return -1; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "pending_flex_downtime",
        "Number of pending flexible downtimes", offsets,
        [](const service &r) { return r.pending_flex_downtime; }));
    table->addColumn(std::make_unique<IntColumn<service>>(
        prefix + "check_flapping_recovery_notification",
        "Whether to check to send a recovery notification when flapping stops (0/1)",
        offsets, [](const service &r) {
            return r.check_flapping_recovery_notification;
        }));
}

void TableServices::answerQuery(Query &query, const User &user) {
    auto process = [&](const service &svc) {
        return !user.is_authorized_for_service(svc) ||
               query.processDataset(Row{&svc});
    };

    // If we know the host, we use it directly.
    if (auto value = query.stringValueRestrictionFor("host_name")) {
        Debug(logger()) << "using host name index with '" << *value << "'";
        if (const auto *hst =
                reinterpret_cast<host *>(core()->find_host(*value))) {
            for (const auto *m = hst->services; m != nullptr; m = m->next) {
                if (!process(*m->service_ptr)) {
                    return;
                }
            }
            return;
        }
    }

    // If we know the service group, we simply iterate over it.
    if (auto value = query.stringValueRestrictionFor("groups")) {
        Debug(logger()) << "using service group index with '" << *value << "'";
        if (const auto *sg =
                find_servicegroup(const_cast<char *>(value->c_str()))) {
            for (const auto *m = sg->members; m != nullptr; m = m->next) {
                if (!process(*m->service_ptr)) {
                    return;
                }
            }
        }
        return;
    }

    // If we know the host group, we simply iterate over it.
    if (auto value = query.stringValueRestrictionFor("host_groups")) {
        Debug(logger()) << "using host group index with '" << *value << "'";
        if (const auto *hg =
                find_hostgroup(const_cast<char *>(value->c_str()))) {
            for (const auto *m = hg->members; m != nullptr; m = m->next) {
                for (const auto *smem = m->host_ptr->services; smem != nullptr;
                     smem = smem->next) {
                    if (!process(*smem->service_ptr)) {
                        return;
                    }
                }
            }
        }
        return;
    }

    // In the general case, we have to process all services.
    Debug(logger()) << "using full table scan";
    for (const auto *svc = service_list; svc != nullptr; svc = svc->next) {
        if (!process(*svc)) {
            return;
        }
    }
}

Row TableServices::get(const std::string &primary_key) const {
    // "host_name;description" is the primary key
    const auto &[host_name, description] = mk::splitCompositeKey2(primary_key);
    return Row(core()->find_service(host_name, description));
}
