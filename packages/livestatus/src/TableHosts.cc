// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableHosts.h"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <optional>
#include <sstream>
#include <unordered_map>
#include <variant>  // IWYU pragma: keep
#include <vector>

#include "livestatus/AttributeBitmaskColumn.h"
#include "livestatus/AttributeListColumn.h"
#include "livestatus/BlobColumn.h"
#include "livestatus/Column.h"
#include "livestatus/CommentRenderer.h"
#include "livestatus/DictColumn.h"
#include "livestatus/DoubleColumn.h"
#include "livestatus/DowntimeRenderer.h"
#include "livestatus/DynamicColumn.h"
#include "livestatus/DynamicFileColumn.h"
#include "livestatus/DynamicRRDColumn.h"
#include "livestatus/HostListRenderer.h"
#include "livestatus/ICore.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/ListColumn.h"
#include "livestatus/LogEntry.h"
#include "livestatus/Logger.h"
#include "livestatus/LogwatchList.h"
#include "livestatus/MapUtils.h"
#include "livestatus/PnpUtils.h"
#include "livestatus/Query.h"
#include "livestatus/RRDColumn.h"
#include "livestatus/ServiceListRenderer.h"
#include "livestatus/ServiceListState.h"
#include "livestatus/StringColumn.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/User.h"
#include "livestatus/mk_inventory.h"

namespace {
std::vector<::column::service_list::Entry> getServices(const IHost &hst,
                                                       const User &user) {
    std::vector<::column::service_list::Entry> entries{};

    hst.all_of_services([&user, &entries](const IService &s) {
        if (user.is_authorized_for_service(s)) {
            entries.emplace_back(
                s.description(), static_cast<ServiceState>(s.current_state()),
                s.has_been_checked(), s.plugin_output(),
                static_cast<ServiceState>(s.last_hard_state()),
                s.current_attempt(), s.max_check_attempts(),
                s.scheduled_downtime_depth(), s.problem_has_been_acknowledged(),
                s.in_custom_time_period());
        }
        return true;
    });
    return entries;
}
}  // namespace

TableHosts::TableHosts(ICore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{}, LockComments::yes,
               LockDowntimes::yes);
}

std::string TableHosts::name() const { return "hosts"; }

std::string TableHosts::namePrefix() const { return "host_"; }

// static
void TableHosts::addColumns(Table *table, const std::string &prefix,
                            const ColumnOffsets &offsets,
                            LockComments lock_comments,
                            LockDowntimes lock_downtimes) {
    auto *mc = table->core();
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "name", "Host name", offsets,
        [](const IHost &r) { return r.name(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "display_name", "Optional display name", offsets,
        [](const IHost &r) { return r.display_name(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "alias", "An alias name for the host", offsets,
        [](const IHost &r) { return r.alias(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "address", "IP address", offsets,
        [](const IHost &r) { return r.ip_address(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "check_command", "Logical command name for active checks",
        offsets, [](const IHost &r) { return r.check_command(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "check_command_expanded",
        "Logical command name for active checks, with macros expanded", offsets,
        [](const IHost &r) { return r.check_command_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "event_handler", "Command used as event handler", offsets,
        [](const IHost &r) { return r.event_handler(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "notification_period",
        "Time period in which problems of this object will be notified. If empty then notification will be always",
        offsets, [](const IHost &r) { return r.notification_period(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "check_period",
        "Time period in which this object will be checked. If empty then the check will always be executed.",
        offsets, [](const IHost &r) { return r.check_period(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "service_period",
        "Time period during which the object is expected to be available",
        offsets, [](const IHost &r) { return r.servicePeriodName(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "notes",
        "Optional notes for this object, with macros not expanded", offsets,
        [](const IHost &r) { return r.notes(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "notes_expanded",
        "The same as notes, but with the most important macros expanded",
        offsets, [](const IHost &r) { return r.notes_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "notes_url",
        "An optional URL with further information about the object", offsets,
        [](const IHost &r) { return r.notes_url(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "notes_url_expanded",
        "Same es notes_url, but with the most important macros expanded",
        offsets, [](const IHost &r) { return r.notes_url_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "action_url",
        "An optional URL to custom actions or information about this host",
        offsets, [](const IHost &r) { return r.action_url(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "action_url_expanded",
        "The same as action_url, but with the most important macros expanded",
        offsets, [](const IHost &r) { return r.action_url_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "plugin_output", "Output of the last check", offsets,
        [](const IHost &r) { return r.plugin_output(); }));
    table->addColumn(std::make_unique<StringColumnPerfData<IHost>>(
        prefix + "perf_data", "Optional performance data of the last check",
        offsets, [](const IHost &r) { return r.perf_data(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "icon_image",
        "The name of an image file to be used in the web pages", offsets,
        [](const IHost &r) { return r.icon_image(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "icon_image_expanded",
        "The same as icon_image, but with the most important macros expanded",
        offsets, [](const IHost &r) { return r.icon_image_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "icon_image_alt", "Alternative text for the icon_image",
        offsets, [](const IHost &r) { return r.icon_image_alt(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "statusmap_image",
        "The name of in image file for the status map", offsets,
        [](const IHost &r) { return r.status_map_image(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "long_plugin_output", "Long (extra) output of the last check",
        offsets, [](const IHost &r) { return r.long_plugin_output(); }));

    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "initial_state", "Initial state", offsets,
        [](const IHost &r) { return r.initial_state(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "max_check_attempts",
        "Maximum attempts for active checks before a hard state", offsets,
        [](const IHost &r) { return r.max_check_attempts(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled (0/1)", offsets,
        [](const IHost &r) { return r.flap_detection_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "check_freshness",
        "Whether freshness checks are enabled (0/1)", offsets,
        [](const IHost &r) { return r.check_freshness(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled (0/1)", offsets,
        [](const IHost &r) { return r.process_performance_data(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)", offsets,
        [](const IHost &r) { return r.accept_passive_host_checks(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "event_handler_enabled",
        "Whether event handling is enabled (0/1)", offsets,
        [](const IHost &r) { return r.event_handler_enabled(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "acknowledgement_type",
        "Type of acknowledgement (0: none, 1: normal, 2: sticky)", offsets,
        [](const IHost &r) { return r.acknowledgement_type(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "check_type", "Type of check (0: active, 1: passive)", offsets,
        [](const IHost &r) { return r.check_type(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "last_state", "State before last state change", offsets,
        [](const IHost &r) { return r.last_state(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "last_hard_state", "Last hard state", offsets,
        [](const IHost &r) { return r.last_hard_state(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "current_attempt", "Number of the current check attempts",
        offsets, [](const IHost &r) { return r.current_attempt(); }));

    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)", offsets,
        [](const IHost &r) { return r.last_notification(); }));
    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)", offsets,
        [](const IHost &r) { return r.next_notification(); }));
    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "next_check",
        "Scheduled time for the next check (Unix timestamp)", offsets,
        [](const IHost &r) { return r.next_check(); }));
    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "last_hard_state_change",
        "Time of the last hard state change - soft or hard (Unix timestamp)",
        offsets, [](const IHost &r) { return r.last_hard_state_change(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "has_been_checked",
        "Whether a check has already been executed (0/1)", offsets,
        [](const IHost &r) { return r.has_been_checked(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "current_notification_number",
        "Number of the current notification", offsets,
        [](const IHost &r) { return r.current_notification_number(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "pending_flex_downtime",
        "Number of pending flexible downtimes", offsets,
        [](const IHost &r) { return r.pending_flex_downtime(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "total_services", "The total number of services of the host",
        offsets, [](const IHost &r) { return r.total_services(); }));
    // Note: this is redundant with "active_checks_enabled". Nobody noted this
    // before...
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "checks_enabled",
        "Whether checks of the object are enabled (0/1)", offsets,
        [](const IHost &r) { return r.active_checks_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "notifications_enabled",
        "Whether notifications of the host are enabled (0/1)", offsets,
        [](const IHost &r) { return r.notifications_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "acknowledged",
        "Whether the current problem has been acknowledged (0/1)", offsets,
        [](const IHost &r) { return r.problem_has_been_acknowledged(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "state",
        "The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN",
        offsets, [](const IHost &r) { return r.current_state(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "state_type", "Type of the current state (0: soft, 1: hard)",
        offsets, [](const IHost &r) { return r.state_type(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)", offsets,
        [](const IHost &r) { return r.no_more_notifications(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "check_flapping_recovery_notification",
        "Whether to check to send a recovery notification when flapping stops (0/1)",
        offsets, [](const IHost &r) {
            return r.check_flapping_recovery_notification();
        }));

    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "last_check", "Time of the last check (Unix timestamp)",
        offsets, [](const IHost &r) { return r.last_check(); }));
    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "last_state_change",
        "Time of the last state change - soft or hard (Unix timestamp)",
        offsets, [](const IHost &r) { return r.last_state_change(); }));

    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "last_time_up",
        "The last time the host was UP (Unix timestamp)", offsets,
        [](const IHost &r) { return r.last_time_up(); }));
    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "last_time_down",
        "The last time the host was DOWN (Unix timestamp)", offsets,
        [](const IHost &r) { return r.last_time_down(); }));
    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "last_time_unreachable",
        "The last time the host was UNREACHABLE (Unix timestamp)", offsets,
        [](const IHost &r) { return r.last_time_unreachable(); }));

    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "is_flapping", "Whether the state is flapping (0/1)", offsets,
        [](const IHost &r) { return r.is_flapping(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "scheduled_downtime_depth",
        "The number of downtimes this object is currently in", offsets,
        [](const IHost &r) { return r.scheduled_downtime_depth(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "is_executing", "is there a check currently running (0/1)",
        offsets, [](const IHost &r) { return r.is_executing(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "active_checks_enabled",
        "Whether active checks of the object are enabled (0/1)", offsets,
        [](const IHost &r) { return r.active_checks_enabled(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness (0-2)", offsets,
        [](const IHost &r) { return r.check_options(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "obsess_over_host",
        "The current obsess_over_host setting (0/1)", offsets,
        [](const IHost &r) { return r.obsess_over_host(); }));
    table->addColumn(std::make_unique<AttributeBitmaskColumn<IHost>>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified", offsets,
        [](const IHost &r) { return r.modified_attributes(); }));
    table->addColumn(
        std::make_unique<
            AttributeListColumn<IHost, column::attribute_list::AttributeBit>>(
            prefix + "modified_attributes_list",
            "A list of all modified attributes", offsets, [](const IHost &r) {
                return column::attribute_list::encode(r.modified_attributes());
            }));

    // columns of type double
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks",
        offsets, [](const IHost &r) { return r.check_interval(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a soft error",
        offsets, [](const IHost &r) { return r.retry_interval(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "notification_interval",
        "Interval of periodic notification in minutes or 0 if its off", offsets,
        [](const IHost &r) { return r.notification_interval(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "first_notification_delay",
        "Delay before the first notification", offsets,
        [](const IHost &r) { return r.first_notification_delay(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        offsets, [](const IHost &r) { return r.low_flap_threshold(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        offsets, [](const IHost &r) { return r.high_flap_threshold(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "x_3d", "3D-Coordinates: X", offsets,
        [](const IHost &r) { return r.x_3d(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "y_3d", "3D-Coordinates: Y", offsets,
        [](const IHost &r) { return r.y_3d(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "z_3d", "3D-Coordinates: Z", offsets,
        [](const IHost &r) { return r.z_3d(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        offsets, [](const IHost &r) { return r.latency(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "execution_time", "Time the check needed for execution",
        offsets, [](const IHost &r) { return r.execution_time(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "percent_state_change", "Percent state change", offsets,
        [](const IHost &r) { return r.percent_state_change(); }));

    table->addColumn(std::make_unique<BoolColumn<IHost, true>>(
        prefix + "in_notification_period",
        "Whether this object is currently in its notification period (0/1)",
        offsets, [](const IHost &r) { return r.in_notification_period(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost, true>>(
        prefix + "in_check_period",
        "Whether this object is currently in its check period (0/1)", offsets,
        [](const IHost &r) { return r.in_check_period(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost, true>>(
        prefix + "in_service_period",
        "Whether this object is currently in its service period (0/1)", offsets,
        [](const IHost &r) { return r.in_service_period(); }));

    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "contacts", "A list of all contacts of this object", offsets,
        [](const IHost &r) { return r.contacts(); }));

    auto get_downtimes = [mc, lock_downtimes](const IHost &r) {
        return lock_downtimes == LockDowntimes::yes ? mc->downtimes(r)
                                                    : mc->downtimes_unlocked(r);
    };
    table->addColumn(
        std::make_unique<ListColumn<IHost, std::unique_ptr<const IDowntime>>>(
            prefix + "downtimes",
            "A list of the ids of all scheduled downtimes of this object",
            offsets,
            std::make_unique<DowntimeRenderer>(
                DowntimeRenderer::verbosity::none),
            get_downtimes));
    table->addColumn(
        std::make_unique<ListColumn<IHost, std::unique_ptr<const IDowntime>>>(
            prefix + "downtimes_with_info",
            "A list of the scheduled downtimes with id, author and comment",
            offsets,
            std::make_unique<DowntimeRenderer>(
                DowntimeRenderer::verbosity::medium),
            get_downtimes));
    table->addColumn(std::make_unique<
                     ListColumn<IHost, std::unique_ptr<const IDowntime>>>(
        prefix + "downtimes_with_extra_info",
        "A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending",
        offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::full),
        get_downtimes));

    auto get_comments = [mc, lock_comments](const IHost &r) {
        return lock_comments == LockComments::yes ? mc->comments(r)
                                                  : mc->comments_unlocked(r);
    };
    table->addColumn(
        std::make_unique<ListColumn<IHost, std::unique_ptr<const IComment>>>(
            prefix + "comments", "A list of the ids of all comments", offsets,
            std::make_unique<CommentRenderer>(CommentRenderer::verbosity::none),
            get_comments));
    table->addColumn(
        std::make_unique<ListColumn<IHost, std::unique_ptr<const IComment>>>(
            prefix + "comments_with_info",
            "A list of all comments with id, author and comment", offsets,
            std::make_unique<CommentRenderer>(
                CommentRenderer::verbosity::medium),
            get_comments));
    table->addColumn(std::make_unique<
                     ListColumn<IHost, std::unique_ptr<const IComment>>>(
        prefix + "comments_with_extra_info",
        "A list of all comments with id, author, comment, entry type and entry time",
        offsets,
        std::make_unique<CommentRenderer>(CommentRenderer::verbosity::full),
        get_comments));

    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables", offsets,
        [](const IHost &r) {
            return mk::map_keys(r.attributes(AttributeKind::custom_variables));
        }));
    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables", offsets,
        [](const IHost &r) {
            return mk::map_values(
                r.attributes(AttributeKind::custom_variables));
        }));
    table->addColumn(std::make_unique<DictColumn<IHost>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets, [](const IHost &r) {
            return r.attributes(AttributeKind::custom_variables);
        }));
    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "tag_names", "A list of the names of the tags", offsets,
        [](const IHost &r) {
            return mk::map_keys(r.attributes(AttributeKind::tags));
        }));
    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "tag_values", "A list of the values of the tags", offsets,
        [](const IHost &r) {
            return mk::map_values(r.attributes(AttributeKind::tags));
        }));
    table->addColumn(std::make_unique<DictColumn<IHost>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        [](const IHost &r) { return r.attributes(AttributeKind::tags); }));
    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "label_names", "A list of the names of the labels", offsets,
        [](const IHost &r) {
            return mk::map_keys(r.attributes(AttributeKind::labels));
        }));
    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "label_values", "A list of the values of the labels", offsets,
        [](const IHost &r) {
            return mk::map_values(r.attributes(AttributeKind::labels));
        }));
    table->addColumn(std::make_unique<DictColumn<IHost>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        [](const IHost &r) { return r.attributes(AttributeKind::labels); }));

    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "label_source_names",
        "A list of the names of the label sources", offsets,
        [](const IHost &r) {
            return mk::map_keys(r.attributes(AttributeKind::label_sources));
        }));
    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "label_source_values",
        "A list of the values of the label sources", offsets,
        [](const IHost &r) {
            return mk::map_values(r.attributes(AttributeKind::label_sources));
        }));
    table->addColumn(std::make_unique<DictColumn<IHost>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        [](const IHost &r) {
            return r.attributes(AttributeKind::label_sources);
        }));

    // Add direct access to the custom macro _FILENAME. In a future version of
    // Livestatus this will probably be configurable so access to further custom
    // variable can be added, such that those variables are presented like
    // ordinary Nagios columns.
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "filename", "The value of the custom variable FILENAME",
        offsets, [](const IHost &r) { return r.filename(); }));

    table->addColumn(
        std::make_unique<ListColumn<IHost, column::host_list::Entry>>(
            prefix + "parents", "A list of all direct parents of the host",
            offsets,
            std::make_unique<HostListRenderer>(
                HostListRenderer::verbosity::none),
            [](const IHost &r, const User &user) {
                std::vector<column::host_list::Entry> entries{};
                r.all_of_parents([&user, &entries](const IHost &h) {
                    if (user.is_authorized_for_host(h)) {
                        entries.emplace_back(
                            h.name(), static_cast<HostState>(h.current_state()),
                            h.has_been_checked());
                    }
                    return true;
                });
                return entries;
            }));
    // TODO(sp): Can we fix the spelling "childs" here, too?
    table->addColumn(
        std::make_unique<ListColumn<IHost, column::host_list::Entry>>(
            prefix + "childs", "A list of all direct children of the host",
            offsets,
            std::make_unique<HostListRenderer>(
                HostListRenderer::verbosity::none),
            [](const IHost &r, const User &user) {
                std::vector<column::host_list::Entry> entries{};
                r.all_of_children([&user, &entries](const IHost &h) {
                    if (user.is_authorized_for_host(h)) {
                        entries.emplace_back(
                            h.name(), static_cast<HostState>(h.current_state()),
                            h.has_been_checked());
                    }
                    return true;
                });
                return entries;
            }));
    table->addDynamicColumn(std::make_unique<DynamicRRDColumn<
                                ListColumn<IHost, RRDDataMaker::value_type>>>(
        prefix + "rrddata",
        "RRD metrics data of this object. This is a column with parameters: rrddata:COLUMN_TITLE:VARNAME:FROM_TIME:UNTIL_TIME:RESOLUTION",
        mc, offsets));

    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services", "The total number of services of the host",
        offsets, ServiceListState{ServiceListState::Type::num}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "worst_service_state",
        "The worst soft state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets, ServiceListState{ServiceListState::Type::worst_state}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_ok",
        "The number of the host's services with the soft state OK", offsets,
        ServiceListState{ServiceListState::Type::num_ok}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_warn",
        "The number of the host's services with the soft state WARN", offsets,
        ServiceListState{ServiceListState::Type::num_warn}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_crit",
        "The number of the host's services with the soft state CRIT", offsets,
        ServiceListState{ServiceListState::Type::num_crit}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_unknown",
        "The number of the host's services with the soft state UNKNOWN",
        offsets, ServiceListState{ServiceListState::Type::num_unknown}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_pending",
        "The number of the host's services which have not been checked yet (pending)",
        offsets, ServiceListState{ServiceListState::Type::num_pending}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_handled_problems",
        "The number of the host's services which have handled problems",
        offsets,
        ServiceListState{ServiceListState::Type::num_handled_problems}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_unhandled_problems",
        "The number of the host's services which have unhandled problems",
        offsets,
        ServiceListState{ServiceListState::Type::num_unhandled_problems}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "worst_service_hard_state",
        "The worst hard state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets, ServiceListState{ServiceListState::Type::worst_hard_state}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_hard_ok",
        "The number of the host's services with the hard state OK", offsets,
        ServiceListState{ServiceListState::Type::num_hard_ok}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_hard_warn",
        "The number of the host's services with the hard state WARN", offsets,
        ServiceListState{ServiceListState::Type::num_hard_warn}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_hard_crit",
        "The number of the host's services with the hard state CRIT", offsets,
        ServiceListState{ServiceListState::Type::num_hard_crit}));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "num_services_hard_unknown",
        "The number of the host's services with the hard state UNKNOWN",
        offsets, ServiceListState{ServiceListState::Type::num_hard_unknown}));

    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "hard_state", "The effective hard state of this object",
        offsets, [](const IHost &r) { return r.hard_state(); }));
    table->addColumn(std::make_unique<BoolColumn<IHost>>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this object (-1/0/1)",
        offsets, [mc](const IHost &r) { return mc->isPnpGraphPresent(r); }));
    table->addColumn(std::make_unique<TimeColumn<IHost>>(
        prefix + "mk_inventory_last",
        "The timestamp of the last Check_MK HW/SW-Inventory for this host. 0 means that no inventory data is present",
        offsets, [mc](const IHost &r) {
            return mk_inventory_last(mc->paths()->inventory_directory() /
                                     r.name());
        }));

    table->addColumn(std::make_unique<BlobColumn<IHost>>(
        prefix + "mk_inventory",
        "The file content of the Check_MK HW/SW-Inventory", offsets,
        BlobFileReader<IHost>{
            [mc]() { return mc->paths()->inventory_directory(); },
            [](const IHost &r) { return std::filesystem::path{r.name()}; }}));
    table->addColumn(std::make_unique<BlobColumn<IHost>>(
        prefix + "mk_inventory_gz",
        "The gzipped file content of the Check_MK HW/SW-Inventory", offsets,
        BlobFileReader<IHost>{
            [mc]() { return mc->paths()->inventory_directory(); },
            [](const IHost &r) {
                return std::filesystem::path{r.name() + ".gz"};
            }}));
    table->addColumn(std::make_unique<BlobColumn<IHost>>(
        prefix + "structured_status",
        "The file content of the structured status of the Check_MK HW/SW-Inventory",
        offsets,
        BlobFileReader<IHost>{
            [mc]() { return mc->paths()->structured_status_directory(); },
            [](const IHost &r) { return std::filesystem::path{r.name()}; }}));
    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "mk_logwatch_files",
        "This list of logfiles with problems fetched via mk_logwatch", offsets,
        [mc](const IHost &r, const Column &col) {
            const auto logwatch_directory = mc->paths()->logwatch_directory();
            auto dir = logwatch_directory.empty() || r.name().empty()
                           ? std::filesystem::path()
                           : logwatch_directory / pnp_cleanup(r.name());
            return getLogwatchList(dir, col);
        }));

    table->addDynamicColumn(std::make_unique<DynamicFileColumn<IHost>>(
        prefix + "mk_logwatch_file",
        "This contents of a logfile fetched via mk_logwatch", offsets,
        [mc]() { return mc->paths()->logwatch_directory(); },
        [](const IHost & /*r*/, const std::string &args) {
            return std::filesystem::path{args};
        }));

    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "staleness", "The staleness of this object", offsets,
        [](const IHost &r) { return r.staleness(); }));

    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "groups", "A list of all host groups this object is in",
        offsets, [](const IHost &r, const User &user) {
            std::vector<std::string> group_names;
            r.all_of_host_groups([&user, &group_names](const IHostGroup &g) {
                if (user.is_authorized_for_host_group(g)) {
                    group_names.emplace_back(g.name());
                }
                return true;
            });
            return group_names;
        }));
    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "contact_groups",
        "A list of all contact groups this object is in", offsets,
        [](const IHost &r) {
            std::vector<std::string> names;
            r.all_of_contact_groups([&names](const IContactGroup &g) {
                names.emplace_back(g.name());
                return true;
            });
            return names;
        }));

    table->addColumn(
        std::make_unique<ListColumn<IHost, ::column::service_list::Entry>>(
            prefix + "services", "A list of all services of the host", offsets,
            std::make_unique<ServiceListRenderer>(
                ServiceListRenderer::verbosity::none),
            getServices));
    table->addColumn(std::make_unique<
                     ListColumn<IHost, ::column::service_list::Entry>>(
        prefix + "services_with_state",
        "A list of all services of the host together with state and has_been_checked",
        offsets,
        std::make_unique<ServiceListRenderer>(
            ServiceListRenderer::verbosity::low),
        getServices));
    table->addColumn(std::make_unique<
                     ListColumn<IHost, ::column::service_list::Entry>>(
        prefix + "services_with_info",
        "A list of all services including detailed information about each service",
        offsets,
        std::make_unique<ServiceListRenderer>(
            ServiceListRenderer::verbosity::medium),
        getServices));
    table->addColumn(std::make_unique<
                     ListColumn<IHost, ::column::service_list::Entry>>(
        prefix + "services_with_fullstate",
        "A list of all services including full state information. The list of entries can grow in future versions.",
        offsets,
        std::make_unique<ServiceListRenderer>(
            ServiceListRenderer::verbosity::full),
        getServices));

    table->addColumn(std::make_unique<ListColumn<IHost>>(
        prefix + "metrics",
        "A list of all metrics of this object that historically existed",
        offsets,
        [mc](const IHost &r) { return mc->metrics(r, mc->loggerRRD()); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "smartping_timeout",
        "Maximum expected time between two received packets in ms", offsets,
        [](const IHost &r) { return r.smartping_timeout(); }));
    table->addColumn(std::make_unique<DoubleColumn<IHost>>(
        prefix + "flappiness",
        "The current level of flappiness, this corresponds with the recent frequency of state changes",
        offsets, [](const IHost &r) { return r.flappiness(); }));
    table->addColumn(std::make_unique<StringColumn<IHost>>(
        prefix + "notification_postponement_reason",
        "reason for postponing the pending notification, empty if nothing is postponed",
        offsets,
        [](const IHost &r) { return r.notification_postponement_reason(); }));
    table->addColumn(std::make_unique<IntColumn<IHost>>(
        prefix + "previous_hard_state",
        "Previous hard state (that hard state before the current/last hard state)",
        offsets, [](const IHost &r) { return r.previous_hard_state(); }));
}

void TableHosts::answerQuery(Query &query, const User &user) {
    auto process = [&](const IHost &hst) {
        return !user.is_authorized_for_host(hst) ||
               query.processDataset(Row{&hst});
    };

    // If we know the host, we use it directly.
    if (auto value = query.stringValueRestrictionFor("name")) {
        Debug(logger()) << "using host name index with '" << *value << "'";
        if (const auto *h = core()->find_host(*value)) {
            process(*h);
        }
        return;
    }

    // If we know the host group, we simply iterate over it.
    if (auto value = query.stringValueRestrictionFor("groups")) {
        Debug(logger()) << "using host group index with '" << *value << "'";
        if (const auto *hg = core()->find_hostgroup(*value)) {
            hg->all([&process](const IHost &h) { return process(h); });
        }
        return;
    }

    // In the general case, we have to process all hosts.
    Debug(logger()) << "using full table scan";
    core()->all_of_hosts([&process](const IHost &h) { return process(h); });
}

Row TableHosts::get(const std::string &primary_key) const {
    // "name" is the primary key
    return Row{core()->find_host(primary_key)};
}
