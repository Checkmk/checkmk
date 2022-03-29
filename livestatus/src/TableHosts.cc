// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableHosts.h"

#include <algorithm>
#include <chrono>
#include <cstdint>
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
#include "DynamicFileColumn.h"
#include "DynamicRRDColumn.h"
#include "HostListRenderer.h"
#include "IntColumn.h"
#include "ListColumn.h"
#include "LogEntry.h"
#include "Logger.h"
#include "LogwatchList.h"
#include "MacroExpander.h"
#include "Metric.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "RRDColumn.h"
#include "ServiceListRenderer.h"
#include "ServiceListState.h"
#include "StringColumn.h"
#include "TimeColumn.h"
#include "TimeperiodsCache.h"
#include "auth.h"
#include "contact_fwd.h"
#include "mk_inventory.h"
#include "nagios.h"
#include "pnp4nagios.h"

using namespace std::string_literals;

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern TimeperiodsCache *g_timeperiods_cache;

namespace {
bool inCustomTimeperiod(MonitoringCore *mc, service *svc) {
    auto attrs = mc->customAttributes(&svc->custom_variables,
                                      AttributeKind::custom_variables);
    auto it = attrs.find("SERVICE_PERIOD");
    if (it != attrs.end()) {
        return g_timeperiods_cache->inTimeperiod(it->second);
    }
    return true;  // assume 24X7
}

class ServiceListGetter {
public:
    explicit ServiceListGetter(MonitoringCore *mc) : mc_{mc} {}
    std::vector<::column::service_list::Entry> operator()(
        const host &hst, const contact *auth_user) const {
        std::vector<::column::service_list::Entry> entries{};
        for (servicesmember *mem = hst.services; mem != nullptr;
             mem = mem->next) {
            service *svc = mem->service_ptr;
            if (is_authorized_for_svc(mc_->serviceAuthorization(), auth_user,
                                      svc)) {
                entries.emplace_back(
                    svc->description,
                    static_cast<ServiceState>(svc->current_state),
                    svc->has_been_checked != 0,
                    svc->plugin_output == nullptr
                        ? ""
                        : std::string(svc->plugin_output),
                    static_cast<ServiceState>(svc->last_hard_state),
                    svc->current_attempt, svc->max_attempts,
                    svc->scheduled_downtime_depth,
                    svc->problem_has_been_acknowledged != 0,
                    inCustomTimeperiod(mc_, svc));
            }
        }
        return entries;
    }

private:
    MonitoringCore *mc_;
};
}  // namespace

TableHosts::TableHosts(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{});
}

std::string TableHosts::name() const { return "hosts"; }

std::string TableHosts::namePrefix() const { return "host_"; }

// static
void TableHosts::addColumns(Table *table, const std::string &prefix,
                            const ColumnOffsets &offsets) {
    auto offsets_custom_variables{offsets.add(
        [](Row r) { return &r.rawData<host>()->custom_variables; })};
    auto *mc = table->core();
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "name", "Host name", offsets,
        [](const host &r) { return r.name == nullptr ? "" : r.name; }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "display_name", "Optional display name", offsets,
        [](const host &r) {
            return r.display_name == nullptr ? "" : r.display_name;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "alias", "An alias name for the host", offsets,
        [](const host &r) { return r.alias == nullptr ? "" : r.alias; }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "address", "IP address", offsets,
        [](const host &r) { return r.address == nullptr ? "" : r.address; }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "check_command", "Logical command name for active checks",
        offsets, [](const host &r) {
            const auto *cc = nagios_compat_host_check_command(r);
            return cc == nullptr ? "" : cc;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "check_command_expanded",
        "Logical command name for active checks, with macros expanded", offsets,
        [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(
                nagios_compat_host_check_command(r));
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "event_handler", "Command used as event handler", offsets,
        [](const host &r) {
            return r.event_handler == nullptr ? "" : r.event_handler;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "notification_period",
        "Time period in which problems of this object will be notified. If empty then notification will be always",
        offsets, [](const host &r) {
            return r.notification_period == nullptr ? ""
                                                    : r.notification_period;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "check_period",
        "Time period in which this object will be checked. If empty then the check will always be executed.",
        offsets, [](const host &r) {
            return r.check_period == nullptr ? "" : r.check_period;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "service_period",
        "Time period during which the object is expected to be available",
        offsets_custom_variables, [mc](const host &p) {
            auto attrs =
                mc->customAttributes(&p, AttributeKind::custom_variables);
            auto it = attrs.find("SERVICE_PERIOD");
            if (it != attrs.end()) {
                return it->second;
            }
            return ""s;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "notes",
        "Optional notes for this object, with macros not expanded", offsets,
        [](const host &r) { return r.notes == nullptr ? "" : r.notes; }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "notes_expanded",
        "The same as notes, but with the most important macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(r.notes);
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "notes_url",
        "An optional URL with further information about the object", offsets,
        [](const host &r) {
            return r.notes_url == nullptr ? "" : r.notes_url;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "notes_url_expanded",
        "Same es notes_url, but with the most important macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(r.notes_url);
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "action_url",
        "An optional URL to custom actions or information about this host",
        offsets, [](const host &r) {
            return r.action_url == nullptr ? "" : r.action_url;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "action_url_expanded",
        "The same as action_url, but with the most important macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(r.action_url);
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "plugin_output", "Output of the last check", offsets,
        [](const host &r) {
            return r.plugin_output == nullptr ? "" : r.plugin_output;
        }));
    table->addColumn(std::make_unique<StringColumnPerfData<host>>(
        prefix + "perf_data", "Optional performance data of the last check",
        offsets, [](const host &r) {
            return r.perf_data == nullptr ? "" : r.perf_data;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "icon_image",
        "The name of an image file to be used in the web pages", offsets,
        [](const host &r) {
            return r.icon_image == nullptr ? "" : r.icon_image;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "icon_image_expanded",
        "The same as icon_image, but with the most important macros expanded",
        offsets, [mc](const host &r) {
            return HostMacroExpander::make(r, mc)->expandMacros(r.icon_image);
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "icon_image_alt", "Alternative text for the icon_image",
        offsets, [](const host &r) {
            return r.icon_image_alt == nullptr ? "" : r.icon_image_alt;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "statusmap_image",
        "The name of in image file for the status map", offsets,
        [](const host &r) {
            return r.statusmap_image == nullptr ? "" : r.statusmap_image;
        }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "long_plugin_output", "Long (extra) output of the last check",
        offsets, [](const host &r) {
            return r.long_plugin_output == nullptr ? "" : r.long_plugin_output;
        }));

    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "initial_state", "Initial state", offsets,
        [](const host &r) { return r.initial_state; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "max_check_attempts",
        "Maximum attempts for active checks before a hard state", offsets,
        [](const host &r) { return r.max_attempts; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled (0/1)", offsets,
        [](const host &r) { return r.flap_detection_enabled; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "check_freshness",
        "Whether freshness checks are enabled (0/1)", offsets,
        [](const host &r) { return r.check_freshness; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled (0/1)", offsets,
        [](const host &r) { return r.process_performance_data; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)", offsets,
        [](const host &r) {
            return nagios_compat_accept_passive_host_checks(r);
        }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "event_handler_enabled",
        "Whether event handling is enabled (0/1)", offsets,
        [](const host &r) { return r.event_handler_enabled; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "acknowledgement_type",
        "Type of acknowledgement (0: none, 1: normal, 2: sticky)", offsets,
        [](const host &r) { return r.acknowledgement_type; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "check_type", "Type of check (0: active, 1: passive)", offsets,
        [](const host &r) { return r.check_type; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "last_state", "State before last state change", offsets,
        [](const host &r) { return r.last_state; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "last_hard_state", "Last hard state", offsets,
        [](const host &r) { return r.last_hard_state; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "current_attempt", "Number of the current check attempts",
        offsets, [](const host &r) { return r.current_attempt; }));
    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(
                nagios_compat_last_host_notification(r));
        }));
    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(
                nagios_compat_next_host_notification(r));
        }));
    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "next_check",
        "Scheduled time for the next check (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.next_check);
        }));
    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "last_hard_state_change",
        "Time of the last hard state change - soft or hard (Unix timestamp)",
        offsets, [](const host &r) {
            return std::chrono::system_clock::from_time_t(
                r.last_hard_state_change);
        }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "has_been_checked",
        "Whether a check has already been executed (0/1)", offsets,
        [](const host &r) { return r.has_been_checked; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "current_notification_number",
        "Number of the current notification", offsets,
        [](const host &r) { return r.current_notification_number; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "pending_flex_downtime",
        "Number of pending flexible downtimes", offsets,
        [](const host &r) { return r.pending_flex_downtime; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "total_services", "The total number of services of the host",
        offsets, [](const host &r) { return r.total_services; }));
    // Note: this is redundant with "active_checks_enabled". Nobody noted this
    // before...
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "checks_enabled",
        "Whether checks of the object are enabled (0/1)", offsets,
        [](const host &r) { return r.checks_enabled; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "notifications_enabled",
        "Whether notifications of the host are enabled (0/1)", offsets,
        [](const host &r) { return r.notifications_enabled; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "acknowledged",
        "Whether the current problem has been acknowledged (0/1)", offsets,
        [](const host &r) { return r.problem_has_been_acknowledged; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "state",
        "The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN",
        offsets, [](const host &r) { return r.current_state; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "state_type", "Type of the current state (0: soft, 1: hard)",
        offsets, [](const host &r) { return r.state_type; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)", offsets,
        [](const host &r) { return r.no_more_notifications; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "check_flapping_recovery_notification",
        "Whether to check to send a recovery notification when flapping stops (0/1)",
        offsets,
        [](const host &r) { return r.check_flapping_recovery_notification; }));
    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "last_check", "Time of the last check (Unix timestamp)",
        offsets, [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.last_check);
        }));
    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "last_state_change",
        "Time of the last state change - soft or hard (Unix timestamp)",
        offsets, [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.last_state_change);
        }));

    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "last_time_up",
        "The last time the host was UP (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_up);
        }));
    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "last_time_down",
        "The last time the host was DOWN (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(r.last_time_down);
        }));
    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "last_time_unreachable",
        "The last time the host was UNREACHABLE (Unix timestamp)", offsets,
        [](const host &r) {
            return std::chrono::system_clock::from_time_t(
                r.last_time_unreachable);
        }));

    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "is_flapping", "Whether the state is flapping (0/1)", offsets,
        [](const host &r) { return r.is_flapping; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "scheduled_downtime_depth",
        "The number of downtimes this object is currently in", offsets,
        [](const host &r) { return r.scheduled_downtime_depth; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "is_executing", "is there a check currently running (0/1)",
        offsets, [](const host &r) { return r.is_executing; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "active_checks_enabled",
        "Whether active checks of the object are enabled (0/1)", offsets,
        [](const host &r) { return r.checks_enabled; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness (0-2)", offsets,
        [](const host &r) { return r.check_options; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "obsess_over_host",
        "The current obsess_over_host setting (0/1)", offsets,
        [](const host &r) { return nagios_compat_obsess_over_host(r); }));
    table->addColumn(std::make_unique<AttributeBitmaskColumn<host>>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified", offsets,
        [](const host &r) { return r.modified_attributes; }));
    table->addColumn(
        std::make_unique<
            AttributeListColumn<host, column::attribute_list::AttributeBit>>(
            prefix + "modified_attributes_list",
            "A list of all modified attributes", offsets, [](const host &r) {
                return column::attribute_list::encode(r.modified_attributes);
            }));

    // columns of type double
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks",
        offsets, [](const host &r) { return r.check_interval; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a soft error",
        offsets, [](const host &r) { return r.retry_interval; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "notification_interval",
        "Interval of periodic notification in minutes or 0 if its off", offsets,
        [](const host &r) { return r.notification_interval; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "first_notification_delay",
        "Delay before the first notification", offsets,
        [](const host &r) { return r.first_notification_delay; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        offsets, [](const host &r) { return r.low_flap_threshold; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        offsets, [](const host &r) { return r.high_flap_threshold; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "x_3d", "3D-Coordinates: X", offsets,
        [](const host &r) { return r.x_3d; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "y_3d", "3D-Coordinates: Y", offsets,
        [](const host &r) { return r.y_3d; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "z_3d", "3D-Coordinates: Z", offsets,
        [](const host &r) { return r.z_3d; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        offsets, [](const host &r) { return r.latency; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "execution_time", "Time the check needed for execution",
        offsets, [](const host &r) { return r.execution_time; }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "percent_state_change", "Percent state change", offsets,
        [](const host &r) { return r.percent_state_change; }));

    table->addColumn(std::make_unique<BoolColumn<host, true>>(
        prefix + "in_notification_period",
        "Whether this object is currently in its notification period (0/1)",
        offsets, [](const host &r) {
            return g_timeperiods_cache->inTimeperiod(r.notification_period_ptr);
        }));
    table->addColumn(std::make_unique<BoolColumn<host, true>>(
        prefix + "in_check_period",
        "Whether this object is currently in its check period (0/1)", offsets,
        [](const host &r) {
            return g_timeperiods_cache->inTimeperiod(r.check_period_ptr);
        }));
    table->addColumn(std::make_unique<BoolColumn<host, true>>(
        prefix + "in_service_period",
        "Whether this object is currently in its service period (0/1)", offsets,
        [mc](const host &r) {
            auto attrs = mc->customAttributes(&r.custom_variables,
                                              AttributeKind::custom_variables);
            auto it = attrs.find("SERVICE_PERIOD");
            return it == attrs.end() ||
                   g_timeperiods_cache->inTimeperiod(it->second);
        }));

    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "contacts", "A list of all contacts of this object", offsets,
        [](const host &hst) {
            std::unordered_set<std::string> names;
            for (auto *cm = hst.contacts; cm != nullptr; cm = cm->next) {
                names.insert(cm->contact_ptr->name);
            }
            for (auto *cgm = hst.contact_groups; cgm != nullptr;
                 cgm = cgm->next) {
                for (auto *cm = cgm->group_ptr->members; cm != nullptr;
                     cm = cm->next) {
                    names.insert(cm->contact_ptr->name);
                }
            }
            return std::vector<std::string>(names.begin(), names.end());
        }));
    table->addColumn(std::make_unique<ListColumn<host, DowntimeData>>(
        prefix + "downtimes",
        "A list of the ids of all scheduled downtimes of this object", offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::none),
        [mc](const host &hst) {
            return mc->downtimes(
                reinterpret_cast<const MonitoringCore::Host *>(&hst));
        }));
    table->addColumn(std::make_unique<ListColumn<host, DowntimeData>>(
        prefix + "downtimes_with_info",
        "A list of the scheduled downtimes with id, author and comment",
        offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::medium),
        [mc](const host &hst) {
            return mc->downtimes(
                reinterpret_cast<const MonitoringCore::Host *>(&hst));
        }));
    table->addColumn(std::make_unique<ListColumn<host, DowntimeData>>(
        prefix + "downtimes_with_extra_info",
        "A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending",
        offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::full),
        [mc](const host &hst) {
            return mc->downtimes(
                reinterpret_cast<const MonitoringCore::Host *>(&hst));
        }));
    table->addColumn(std::make_unique<ListColumn<host, CommentData>>(
        prefix + "comments", "A list of the ids of all comments", offsets,
        std::make_unique<CommentRenderer>(CommentRenderer::verbosity::none),
        [mc](const host &hst) {
            return mc->comments(
                reinterpret_cast<const MonitoringCore::Host *>(&hst));
        }));
    table->addColumn(std::make_unique<ListColumn<host, CommentData>>(
        prefix + "comments_with_info",
        "A list of all comments with id, author and comment", offsets,
        std::make_unique<CommentRenderer>(CommentRenderer::verbosity::medium),
        [mc](const host &hst) {
            return mc->comments(
                reinterpret_cast<const MonitoringCore::Host *>(&hst));
        }));
    table->addColumn(std::make_unique<ListColumn<host, CommentData>>(
        prefix + "comments_with_extra_info",
        "A list of all comments with id, author, comment, entry type and entry time",
        offsets,
        std::make_unique<CommentRenderer>(CommentRenderer::verbosity::full),
        [mc](const host &hst) {
            return mc->comments(
                reinterpret_cast<const MonitoringCore::Host *>(&hst));
        }));

    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables", offsets,
        CustomAttributeMap::Keys{mc, AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables", offsets,
        CustomAttributeMap::Values{mc, AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<DictColumn<host>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets, CustomAttributeMap{mc, AttributeKind::custom_variables}));

    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "tag_names", "A list of the names of the tags", offsets,
        CustomAttributeMap::Keys{mc, AttributeKind::tags}));
    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "tag_values", "A list of the values of the tags", offsets,
        CustomAttributeMap::Values{mc, AttributeKind::tags}));
    table->addColumn(std::make_unique<DictColumn<host>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        CustomAttributeMap{mc, AttributeKind::tags}));

    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "label_names", "A list of the names of the labels", offsets,
        CustomAttributeMap::Keys{mc, AttributeKind::labels}));
    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "label_values", "A list of the values of the labels", offsets,
        CustomAttributeMap::Values{mc, AttributeKind::labels}));
    table->addColumn(std::make_unique<DictColumn<host>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        CustomAttributeMap{mc, AttributeKind::labels}));

    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "label_source_names",
        "A list of the names of the label sources", offsets,
        CustomAttributeMap::Keys{mc, AttributeKind::label_sources}));
    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "label_source_values",
        "A list of the values of the label sources", offsets,
        CustomAttributeMap::Values{mc, AttributeKind::label_sources}));
    table->addColumn(std::make_unique<DictColumn<host>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        CustomAttributeMap{mc, AttributeKind::label_sources}));

    // Add direct access to the custom macro _FILENAME. In a future version of
    // Livestatus this will probably be configurable so access to further custom
    // variable can be added, such that those variables are presented like
    // ordinary Nagios columns.
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "filename", "The value of the custom variable FILENAME",
        offsets_custom_variables, [mc](const host &p) {
            auto attrs =
                mc->customAttributes(&p, AttributeKind::custom_variables);
            auto it = attrs.find("FILENAME");
            if (it != attrs.end()) {
                return it->second;
            }
            return ""s;
        }));

    table->addColumn(
        std::make_unique<ListColumn<host, column::host_list::Entry>>(
            prefix + "parents", "A list of all direct parents of the host",
            offsets,
            std::make_unique<HostListRenderer>(
                HostListRenderer::verbosity::none),
            column::host_list::HostListGetter<host>{
                [](const host &r) { return r.parent_hosts; }}));
    table->addColumn(
        std::make_unique<ListColumn<host, column::host_list::Entry>>(
            prefix + "childs", "A list of all direct children of the host",
            offsets,
            std::make_unique<HostListRenderer>(
                HostListRenderer::verbosity::none),
            column::host_list::HostListGetter<host>{
                [](const host &r) { return r.child_hosts; }}));
    table->addDynamicColumn(std::make_unique<DynamicRRDColumn<
                                ListColumn<host, RRDDataMaker::value_type>>>(
        prefix + "rrddata",
        "RRD metrics data of this object. This is a column with parameters: rrddata:COLUMN_TITLE:VARNAME:FROM_TIME:UNTIL_TIME:RESOLUTION",
        mc, offsets));

    auto get_service_auth = [mc]() { return mc->serviceAuthorization(); };
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services", "The total number of services of the host",
        offsets,
        ServiceListState{get_service_auth, ServiceListState::Type::num}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "worst_service_state",
        "The worst soft state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::worst_state}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_ok",
        "The number of the host's services with the soft state OK", offsets,
        ServiceListState{get_service_auth, ServiceListState::Type::num_ok}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_warn",
        "The number of the host's services with the soft state WARN", offsets,
        ServiceListState{get_service_auth, ServiceListState::Type::num_warn}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_crit",
        "The number of the host's services with the soft state CRIT", offsets,
        ServiceListState{get_service_auth, ServiceListState::Type::num_crit}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_unknown",
        "The number of the host's services with the soft state UNKNOWN",
        offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::num_unknown}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_pending",
        "The number of the host's services which have not been checked yet (pending)",
        offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::num_pending}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_handled_problems",
        "The number of the host's services which have handled problems",
        offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::num_handled_problems}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_unhandled_problems",
        "The number of the host's services which have unhandled problems",
        offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::num_unhandled_problems}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "worst_service_hard_state",
        "The worst hard state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::worst_hard_state}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_hard_ok",
        "The number of the host's services with the hard state OK", offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::num_hard_ok}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_hard_warn",
        "The number of the host's services with the hard state WARN", offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::num_hard_warn}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_hard_crit",
        "The number of the host's services with the hard state CRIT", offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::num_hard_crit}));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "num_services_hard_unknown",
        "The number of the host's services with the hard state UNKNOWN",
        offsets,
        ServiceListState{get_service_auth,
                         ServiceListState::Type::num_hard_unknown}));

    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "hard_state", "The effective hard state of this object",
        offsets, [](const host &hst) {
            if (hst.current_state == HOST_UP) {
                return 0;
            }
            return hst.state_type == HARD_STATE ? hst.current_state
                                                : hst.last_hard_state;
        }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this object (-1/0/1)",
        offsets, [mc](const host &hst) {
            return pnpgraph_present(mc, hst.name, dummy_service_description());
        }));
    table->addColumn(std::make_unique<TimeColumn<host>>(
        prefix + "mk_inventory_last",
        "The timestamp of the last Check_MK HW/SW-Inventory for this host. 0 means that no inventory data is present",
        offsets, [mc](const host &hst) {
            return mk_inventory_last(mc->mkInventoryPath() / hst.name);
        }));

    table->addColumn(std::make_unique<BlobColumn<host>>(
        prefix + "mk_inventory",
        "The file content of the Check_MK HW/SW-Inventory", offsets,
        BlobFileReader<host>{
            [mc]() { return mc->mkInventoryPath(); },
            [](const host &r) { return std::filesystem::path{r.name}; }}));
    table->addColumn(std::make_unique<BlobColumn<host>>(
        prefix + "mk_inventory_gz",
        "The gzipped file content of the Check_MK HW/SW-Inventory", offsets,
        BlobFileReader<host>{[mc]() { return mc->mkInventoryPath(); },
                             [](const host &r) {
                                 return std::filesystem::path{
                                     std::string{r.name} + ".gz"};
                             }}));
    table->addColumn(std::make_unique<BlobColumn<host>>(
        prefix + "structured_status",
        "The file content of the structured status of the Check_MK HW/SW-Inventory",
        offsets,
        BlobFileReader<host>{
            [mc]() { return mc->structuredStatusPath(); },
            [](const host &r) { return std::filesystem::path{r.name}; }}));
    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "mk_logwatch_files",
        "This list of logfiles with problems fetched via mk_logwatch", offsets,
        [mc](const host &hst, const Column &col) {
            auto dir =
                mc->mkLogwatchPath().empty() || std::string{hst.name}.empty()
                    ? std::filesystem::path()
                    : std::filesystem::path(mc->mkLogwatchPath()) /
                          pnp_cleanup(hst.name);
            return getLogwatchList(dir, col);
        }));

    table->addDynamicColumn(std::make_unique<DynamicFileColumn<host>>(
        prefix + "mk_logwatch_file",
        "This contents of a logfile fetched via mk_logwatch", offsets,
        [mc]() { return mc->mkLogwatchPath(); },
        [](const host & /*r*/, const std::string &args) {
            return std::filesystem::path{args};
        }));

    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "staleness", "The staleness of this object", offsets,
        [](const host &hst) {
            auto now = std::chrono::system_clock::to_time_t(
                std::chrono::system_clock::now());
            return static_cast<double>(now - hst.last_check) /
                   ((hst.check_interval == 0 ? 1 : hst.check_interval) *
                    interval_length);
        }));

    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "groups", "A list of all host groups this object is in",
        offsets, [mc](const host &hst, const contact *auth_user) {
            std::vector<std::string> group_names;
            for (objectlist *list = hst.hostgroups_ptr; list != nullptr;
                 list = list->next) {
                auto *hg = static_cast<hostgroup *>(list->object_ptr);
                if (is_authorized_for_host_group(mc->groupAuthorization(), hg,
                                                 auth_user)) {
                    group_names.emplace_back(hg->group_name);
                }
            }
            return group_names;
        }));
    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "contact_groups",
        "A list of all contact groups this object is in", offsets,
        [](const host &hst) {
            std::vector<std::string> names;
            for (const auto *cgm = hst.contact_groups; cgm != nullptr;
                 cgm = cgm->next) {
                names.emplace_back(cgm->group_ptr->group_name);
            }
            return names;
        }));

    table->addColumn(
        std::make_unique<ListColumn<host, ::column::service_list::Entry>>(
            prefix + "services", "A list of all services of the host", offsets,
            std::make_unique<ServiceListRenderer>(
                ServiceListRenderer::verbosity::none),
            ServiceListGetter{mc}));
    table->addColumn(std::make_unique<
                     ListColumn<host, ::column::service_list::Entry>>(
        prefix + "services_with_state",
        "A list of all services of the host together with state and has_been_checked",
        offsets,
        std::make_unique<ServiceListRenderer>(
            ServiceListRenderer::verbosity::low),
        ServiceListGetter{mc}));
    table->addColumn(std::make_unique<
                     ListColumn<host, ::column::service_list::Entry>>(
        prefix + "services_with_info",
        "A list of all services including detailed information about each service",
        offsets,
        std::make_unique<ServiceListRenderer>(
            ServiceListRenderer::verbosity::medium),
        ServiceListGetter{mc}));
    table->addColumn(std::make_unique<
                     ListColumn<host, ::column::service_list::Entry>>(
        prefix + "services_with_fullstate",
        "A list of all services including full state information. The list of entries can grow in future versions.",
        offsets,
        std::make_unique<ServiceListRenderer>(
            ServiceListRenderer::verbosity::full),
        ServiceListGetter{mc}));

    table->addColumn(std::make_unique<ListColumn<host>>(
        prefix + "metrics",
        "A list of all metrics of this object that historically existed",
        offsets, [mc](const host &r) {
            std::vector<std::string> metrics;
            if (r.name != nullptr) {
                auto names =
                    scan_rrd(mc->pnpPath() / r.name,
                             dummy_service_description(), mc->loggerRRD());
                std::transform(std::begin(names), std::end(names),
                               std::back_inserter(metrics),
                               [](auto &&m) { return m.string(); });
            }
            return metrics;
        }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "smartping_timeout",
        "Maximum expected time between two received packets in ms", offsets,
        [](const host &r) {
            // Let's pretend the default. Or should we simply use 0?
            return static_cast<int32_t>(r.check_interval * 60000 * 2.5);
        }));
    table->addColumn(std::make_unique<DoubleColumn<host>>(
        prefix + "flappiness",
        "The current level of flappiness, this corresponds with the recent frequency of state changes",
        offsets, [](const host &r) { return r.percent_state_change; }));
    table->addColumn(std::make_unique<StringColumn<host>>(
        prefix + "notification_postponement_reason",
        "reason for postponing the pending notification, empty if nothing is postponed",
        offsets, [](const host & /*r*/) { return ""; }));
    table->addColumn(std::make_unique<IntColumn<host>>(
        prefix + "previous_hard_state",
        "Previous hard state (that hard state before the current/last hard state)",
        offsets, [](const host & /*r*/) { return -1; }));
}

void TableHosts::answerQuery(Query *query, const User &user) {
    auto process = [&](const host &hst) {
        return !user.is_authorized_for_host(hst) ||
               query->processDataset(Row{&hst});
    };

    // If we know the host, we use it directly.
    if (auto value = query->stringValueRestrictionFor("name")) {
        Debug(logger()) << "using host name index with '" << *value << "'";
        if (const auto *hst =
                reinterpret_cast<const host *>(core()->find_host(*value))) {
            process(*hst);
        }
        return;
    }

    // If we know the host group, we simply iterate over it.
    if (auto value = query->stringValueRestrictionFor("groups")) {
        Debug(logger()) << "using host group index with '" << *value << "'";
        if (const auto *hg =
                find_hostgroup(const_cast<char *>(value->c_str()))) {
            for (const auto *m = hg->members; m != nullptr; m = m->next) {
                if (!process(*m->host_ptr)) {
                    return;
                }
            }
        }
        return;
    }

    // In the general case, we have to process all hosts.
    Debug(logger()) << "using full table scan";
    for (const auto *hst = host_list; hst != nullptr; hst = hst->next) {
        if (!process(*hst)) {
            return;
        }
    }
}

Row TableHosts::get(const std::string &primary_key) const {
    // "name" is the primary key
    return Row(core()->find_host(primary_key));
}
