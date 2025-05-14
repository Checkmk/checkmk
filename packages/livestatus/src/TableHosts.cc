// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableHosts.h"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <iterator>
#include <memory>
#include <optional>
#include <unordered_map>
#include <utility>
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
#include "livestatus/Logger.h"
#include "livestatus/LogwatchList.h"
#include "livestatus/MapUtils.h"
#include "livestatus/PerformanceData.h"
#include "livestatus/PnpUtils.h"
#include "livestatus/Query.h"
#include "livestatus/RRDColumn.h"
#include "livestatus/Row.h"
#include "livestatus/ServiceListRenderer.h"
#include "livestatus/ServiceListState.h"
#include "livestatus/StringColumn.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/User.h"
#include "livestatus/mk_inventory.h"

enum class HostState;

using row_type = IHost;

namespace {
std::vector<::column::service_list::Entry> getServices(const row_type &row,
                                                       const User &user) {
    std::vector<::column::service_list::Entry> entries{};

    row.all_of_services([&user, &entries](const IService &s) {
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

TableHosts::TableHosts(ICore *mc) {
    addColumns(this, *mc, "", ColumnOffsets{}, LockComments::yes,
               LockDowntimes::yes);
}

std::string TableHosts::name() const { return "hosts"; }

std::string TableHosts::namePrefix() const { return "host_"; }

// static
void TableHosts::addColumns(Table *table, const ICore &core,
                            const std::string &prefix,
                            const ColumnOffsets &offsets,
                            LockComments lock_comments,
                            LockDowntimes lock_downtimes) {
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "name", "Host name", offsets,
        [](const row_type &row) { return row.name(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "display_name", "Optional display name", offsets,
        [](const row_type &row) { return row.display_name(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "alias", "An alias name for the host", offsets,
        [](const row_type &row) { return row.alias(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "address", "IP address", offsets,
        [](const row_type &row) { return row.ip_address(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "check_command", "Logical command name for active checks",
        offsets, [](const row_type &row) { return row.check_command(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "check_command_expanded",
        "Logical command name for active checks, with macros expanded", offsets,
        [](const row_type &row) { return row.check_command_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "event_handler", "Command used as event handler", offsets,
        [](const row_type &row) { return row.event_handler(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "notification_period",
        "Time period in which problems of this object will be notified. If empty then notification will be always",
        offsets,
        [](const row_type &row) { return row.notification_period(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "check_period",
        "Time period in which this object will be checked. If empty then the check will always be executed.",
        offsets, [](const row_type &row) { return row.check_period(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "service_period",
        "Time period during which the object is expected to be available",
        offsets, [](const row_type &row) { return row.servicePeriodName(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "notes",
        "Optional notes for this object, with macros not expanded", offsets,
        [](const row_type &row) { return row.notes(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "notes_expanded",
        "The same as notes, but with the most important macros expanded",
        offsets, [](const row_type &row) { return row.notes_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "notes_url",
        "An optional URL with further information about the object", offsets,
        [](const row_type &row) { return row.notes_url(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "notes_url_expanded",
        "Same es notes_url, but with the most important macros expanded",
        offsets, [](const row_type &row) { return row.notes_url_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "action_url",
        "An optional URL to custom actions or information about this host",
        offsets, [](const row_type &row) { return row.action_url(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "action_url_expanded",
        "The same as action_url, but with the most important macros expanded",
        offsets,
        [](const row_type &row) { return row.action_url_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "plugin_output", "Output of the last check", offsets,
        [](const row_type &row) { return row.plugin_output(); }));
    table->addColumn(std::make_unique<StringColumnPerfData<row_type>>(
        prefix + "perf_data", "Optional performance data of the last check",
        offsets, [](const row_type &row) { return row.perf_data(); }));
    table->addColumn(std::make_unique<DictDoubleValueColumn<row_type>>(
        prefix + "performance_data", "Optional performance data as a dict",
        offsets, [](const row_type &row) {
            auto d = PerformanceData{row.perf_data(), ""};
            auto out = DictDoubleValueColumn<row_type>::value_type{};
            out.reserve(d.size());
            std::ranges::transform(
                d, std::inserter(out, out.begin()), [](auto &&metric) {
                    return std::make_pair(metric.name().string(),
                                          metric.value_as_double());
                });
            return out;
        }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "icon_image",
        "The name of an image file to be used in the web pages", offsets,
        [](const row_type &row) { return row.icon_image(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "icon_image_expanded",
        "The same as icon_image, but with the most important macros expanded",
        offsets,
        [](const row_type &row) { return row.icon_image_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "icon_image_alt", "Alternative text for the icon_image",
        offsets, [](const row_type &row) { return row.icon_image_alt(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "statusmap_image",
        "The name of in image file for the status map", offsets,
        [](const row_type &row) { return row.status_map_image(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "long_plugin_output", "Long (extra) output of the last check",
        offsets, [](const row_type &row) { return row.long_plugin_output(); }));

    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "initial_state", "Initial state", offsets,
        [](const row_type &row) { return row.initial_state(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "max_check_attempts",
        "Maximum attempts for active checks before a hard state", offsets,
        [](const row_type &row) { return row.max_check_attempts(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled (0/1)", offsets,
        [](const row_type &row) { return row.flap_detection_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "check_freshness",
        "Whether freshness checks are enabled (0/1)", offsets,
        [](const row_type &row) { return row.check_freshness(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled (0/1)", offsets,
        [](const row_type &row) { return row.process_performance_data(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)", offsets,
        [](const row_type &row) { return row.accept_passive_host_checks(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "event_handler_enabled",
        "Whether event handling is enabled (0/1)", offsets,
        [](const row_type &row) { return row.event_handler_enabled(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "acknowledgement_type",
        "Type of acknowledgement (0: none, 1: normal, 2: sticky)", offsets,
        [](const row_type &row) { return row.acknowledgement_type(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "check_type", "Type of check (0: active, 1: passive)", offsets,
        [](const row_type &row) { return row.check_type(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "last_state", "State before last state change", offsets,
        [](const row_type &row) { return row.last_state(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "last_hard_state", "Last hard state", offsets,
        [](const row_type &row) { return row.last_hard_state(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "current_attempt", "Number of the current check attempts",
        offsets, [](const row_type &row) { return row.current_attempt(); }));

    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)", offsets,
        [](const row_type &row) { return row.last_notification(); }));
    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)", offsets,
        [](const row_type &row) { return row.next_notification(); }));
    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "next_check",
        "Scheduled time for the next check (Unix timestamp)", offsets,
        [](const row_type &row) { return row.next_check(); }));
    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "last_hard_state_change",
        "Time of the last hard state change - soft or hard (Unix timestamp)",
        offsets,
        [](const row_type &row) { return row.last_hard_state_change(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "has_been_checked",
        "Whether a check has already been executed (0/1)", offsets,
        [](const row_type &row) { return row.has_been_checked(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "current_notification_number",
        "Number of the current notification", offsets,
        [](const row_type &row) { return row.current_notification_number(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "pending_flex_downtime",
        "Number of pending flexible downtimes", offsets,
        [](const row_type &row) { return row.pending_flex_downtime(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "total_services", "The total number of services of the host",
        offsets, [](const row_type &row) { return row.total_services(); }));
    // Note: this is redundant with "active_checks_enabled". Nobody noted this
    // before...
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "checks_enabled",
        "Whether checks of the object are enabled (0/1)", offsets,
        [](const row_type &row) { return row.active_checks_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "notifications_enabled",
        "Whether notifications of the host are enabled (0/1)", offsets,
        [](const row_type &row) { return row.notifications_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "acknowledged",
        "Whether the current problem has been acknowledged (0/1)", offsets,
        [](const row_type &row) {
            return row.problem_has_been_acknowledged();
        }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "state",
        "The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN",
        offsets, [](const row_type &row) { return row.current_state(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "state_type", "Type of the current state (0: soft, 1: hard)",
        offsets, [](const row_type &row) { return row.state_type(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)", offsets,
        [](const row_type &row) { return row.no_more_notifications(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "check_flapping_recovery_notification",
        "Whether to check to send a recovery notification when flapping stops (0/1)",
        offsets, [](const row_type &row) {
            return row.check_flapping_recovery_notification();
        }));

    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "last_check", "Time of the last check (Unix timestamp)",
        offsets, [](const row_type &row) { return row.last_check(); }));
    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "last_state_change",
        "Time of the last state change - soft or hard (Unix timestamp)",
        offsets, [](const row_type &row) { return row.last_state_change(); }));

    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "last_time_up",
        "The last time the host was UP (Unix timestamp)", offsets,
        [](const row_type &row) { return row.last_time_up(); }));
    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "last_time_down",
        "The last time the host was DOWN (Unix timestamp)", offsets,
        [](const row_type &row) { return row.last_time_down(); }));
    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "last_time_unreachable",
        "The last time the host was UNREACHABLE (Unix timestamp)", offsets,
        [](const row_type &row) { return row.last_time_unreachable(); }));

    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "is_flapping", "Whether the state is flapping (0/1)", offsets,
        [](const row_type &row) { return row.is_flapping(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "scheduled_downtime_depth",
        "The number of downtimes this object is currently in", offsets,
        [](const row_type &row) { return row.scheduled_downtime_depth(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "is_executing", "is there a check currently running (0/1)",
        offsets, [](const row_type &row) { return row.is_executing(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "active_checks_enabled",
        "Whether active checks of the object are enabled (0/1)", offsets,
        [](const row_type &row) { return row.active_checks_enabled(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness (0-2)", offsets,
        [](const row_type &row) { return row.check_options(); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "obsess_over_host",
        "The current obsess_over_host setting (0/1)", offsets,
        [](const row_type &row) { return row.obsess_over_host(); }));
    table->addColumn(std::make_unique<AttributeBitmaskColumn<row_type>>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified", offsets,
        [](const row_type &row) { return row.modified_attributes(); }));
    table->addColumn(std::make_unique<AttributeListColumn<
                         row_type, column::attribute_list::AttributeBit>>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", offsets, [](const row_type &row) {
            return column::attribute_list::encode(row.modified_attributes());
        }));

    // columns of type double
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks",
        offsets, [](const row_type &row) { return row.check_interval(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a soft error",
        offsets, [](const row_type &row) { return row.retry_interval(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "notification_interval",
        "Interval of periodic notification in minutes or 0 if its off", offsets,
        [](const row_type &row) { return row.notification_interval(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "first_notification_delay",
        "Delay before the first notification", offsets,
        [](const row_type &row) { return row.first_notification_delay(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        offsets, [](const row_type &row) { return row.low_flap_threshold(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        offsets,
        [](const row_type &row) { return row.high_flap_threshold(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "x_3d", "3D-Coordinates: X", offsets,
        [](const row_type &row) { return row.x_3d(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "y_3d", "3D-Coordinates: Y", offsets,
        [](const row_type &row) { return row.y_3d(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "z_3d", "3D-Coordinates: Z", offsets,
        [](const row_type &row) { return row.z_3d(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        offsets, [](const row_type &row) { return row.latency(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "execution_time", "Time the check needed for execution",
        offsets, [](const row_type &row) { return row.execution_time(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "percent_state_change", "Percent state change", offsets,
        [](const row_type &row) { return row.percent_state_change(); }));

    table->addColumn(std::make_unique<BoolColumn<row_type, true>>(
        prefix + "in_notification_period",
        "Whether this object is currently in its notification period (0/1)",
        offsets,
        [](const row_type &row) { return row.in_notification_period(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type, true>>(
        prefix + "in_check_period",
        "Whether this object is currently in its check period (0/1)", offsets,
        [](const row_type &row) { return row.in_check_period(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type, true>>(
        prefix + "in_service_period",
        "Whether this object is currently in its service period (0/1)", offsets,
        [](const row_type &row) { return row.in_service_period(); }));

    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "contacts", "A list of all contacts of this object", offsets,
        [](const row_type &row) { return row.contacts(); }));

    auto get_downtimes = [&core, lock_downtimes](const row_type &row) {
        return lock_downtimes == LockDowntimes::yes
                   ? core.downtimes(row)
                   : core.downtimes_unlocked(row);
    };
    table->addColumn(std::make_unique<
                     ListColumn<row_type, std::unique_ptr<const IDowntime>>>(
        prefix + "downtimes",
        "A list of the ids of all scheduled downtimes of this object", offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::none),
        get_downtimes));
    table->addColumn(std::make_unique<
                     ListColumn<row_type, std::unique_ptr<const IDowntime>>>(
        prefix + "downtimes_with_info",
        "A list of the scheduled downtimes with id, author and comment",
        offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::medium),
        get_downtimes));
    table->addColumn(std::make_unique<
                     ListColumn<row_type, std::unique_ptr<const IDowntime>>>(
        prefix + "downtimes_with_extra_info",
        "A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending",
        offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::full),
        get_downtimes));

    auto get_comments = [&core, lock_comments](const row_type &row) {
        return lock_comments == LockComments::yes ? core.comments(row)
                                                  : core.comments_unlocked(row);
    };
    table->addColumn(
        std::make_unique<ListColumn<row_type, std::unique_ptr<const IComment>>>(
            prefix + "comments", "A list of the ids of all comments", offsets,
            std::make_unique<CommentRenderer>(CommentRenderer::verbosity::none),
            get_comments));
    table->addColumn(
        std::make_unique<ListColumn<row_type, std::unique_ptr<const IComment>>>(
            prefix + "comments_with_info",
            "A list of all comments with id, author and comment", offsets,
            std::make_unique<CommentRenderer>(
                CommentRenderer::verbosity::medium),
            get_comments));
    table->addColumn(std::make_unique<
                     ListColumn<row_type, std::unique_ptr<const IComment>>>(
        prefix + "comments_with_extra_info",
        "A list of all comments with id, author, comment, entry type and entry time",
        offsets,
        std::make_unique<CommentRenderer>(CommentRenderer::verbosity::full),
        get_comments));

    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables", offsets,
        [](const row_type &row) {
            return mk::map_keys(
                row.attributes(AttributeKind::custom_variables));
        }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables", offsets,
        [](const row_type &row) {
            return mk::map_values(
                row.attributes(AttributeKind::custom_variables));
        }));
    table->addColumn(std::make_unique<DictStrValueColumn<row_type>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets, [](const row_type &row) {
            return row.attributes(AttributeKind::custom_variables);
        }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "tag_names", "A list of the names of the tags", offsets,
        [](const row_type &row) {
            return mk::map_keys(row.attributes(AttributeKind::tags));
        }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "tag_values", "A list of the values of the tags", offsets,
        [](const row_type &row) {
            return mk::map_values(row.attributes(AttributeKind::tags));
        }));
    table->addColumn(std::make_unique<DictStrValueColumn<row_type>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        [](const row_type &row) {
            return row.attributes(AttributeKind::tags);
        }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "label_names", "A list of the names of the labels", offsets,
        [](const row_type &row) {
            return mk::map_keys(row.attributes(AttributeKind::labels));
        }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "label_values", "A list of the values of the labels", offsets,
        [](const row_type &row) {
            return mk::map_values(row.attributes(AttributeKind::labels));
        }));
    table->addColumn(std::make_unique<DictStrValueColumn<row_type>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        [](const row_type &row) {
            return row.attributes(AttributeKind::labels);
        }));

    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "label_source_names",
        "A list of the names of the label sources", offsets,
        [](const row_type &row) {
            return mk::map_keys(row.attributes(AttributeKind::label_sources));
        }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "label_source_values",
        "A list of the values of the label sources", offsets,
        [](const row_type &row) {
            return mk::map_values(row.attributes(AttributeKind::label_sources));
        }));
    table->addColumn(std::make_unique<DictStrValueColumn<row_type>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        [](const row_type &row) {
            return row.attributes(AttributeKind::label_sources);
        }));

    // Add direct access to the custom macro _FILENAME. In a future version of
    // Livestatus this will probably be configurable so access to further custom
    // variable can be added, such that those variables are presented like
    // ordinary Nagios columns.
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "filename", "The value of the custom variable FILENAME",
        offsets, [](const row_type &row) { return row.filename(); }));

    table->addColumn(
        std::make_unique<ListColumn<row_type, column::host_list::Entry>>(
            prefix + "parents", "A list of all direct parents of the host",
            offsets,
            std::make_unique<HostListRenderer>(
                HostListRenderer::verbosity::none),
            [](const row_type &row, const User &user) {
                std::vector<column::host_list::Entry> entries{};
                row.all_of_parents([&user, &entries](const IHost &h) {
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
        std::make_unique<ListColumn<row_type, column::host_list::Entry>>(
            prefix + "childs", "A list of all direct children of the host",
            offsets,
            std::make_unique<HostListRenderer>(
                HostListRenderer::verbosity::none),
            [](const row_type &row, const User &user) {
                std::vector<column::host_list::Entry> entries{};
                row.all_of_children([&user, &entries](const IHost &h) {
                    if (user.is_authorized_for_host(h)) {
                        entries.emplace_back(
                            h.name(), static_cast<HostState>(h.current_state()),
                            h.has_been_checked());
                    }
                    return true;
                });
                return entries;
            }));
    table->addDynamicColumn(std::make_unique<DynamicRRDColumn<ListColumn<
                                row_type, RRDDataMaker::value_type>>>(
        prefix + "rrddata",
        "RRD metrics data of this object. This is a column with parameters: rrddata:COLUMN_TITLE:VARNAME:FROM_TIME:UNTIL_TIME:RESOLUTION",
        core, offsets));

    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services", "The total number of services of the host",
        offsets, ServiceListState{ServiceListState::Type::num}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "worst_service_state",
        "The worst soft state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets, ServiceListState{ServiceListState::Type::worst_state}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_ok",
        "The number of the host's services with the soft state OK", offsets,
        ServiceListState{ServiceListState::Type::num_ok}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_warn",
        "The number of the host's services with the soft state WARN", offsets,
        ServiceListState{ServiceListState::Type::num_warn}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_crit",
        "The number of the host's services with the soft state CRIT", offsets,
        ServiceListState{ServiceListState::Type::num_crit}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_unknown",
        "The number of the host's services with the soft state UNKNOWN",
        offsets, ServiceListState{ServiceListState::Type::num_unknown}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_pending",
        "The number of the host's services which have not been checked yet (pending)",
        offsets, ServiceListState{ServiceListState::Type::num_pending}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_handled_problems",
        "The number of the host's services which have handled problems",
        offsets,
        ServiceListState{ServiceListState::Type::num_handled_problems}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_unhandled_problems",
        "The number of the host's services which have unhandled problems",
        offsets,
        ServiceListState{ServiceListState::Type::num_unhandled_problems}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "worst_service_hard_state",
        "The worst hard state of all of the host's services (OK <= WARN <= UNKNOWN <= CRIT)",
        offsets, ServiceListState{ServiceListState::Type::worst_hard_state}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_hard_ok",
        "The number of the host's services with the hard state OK", offsets,
        ServiceListState{ServiceListState::Type::num_hard_ok}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_hard_warn",
        "The number of the host's services with the hard state WARN", offsets,
        ServiceListState{ServiceListState::Type::num_hard_warn}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_hard_crit",
        "The number of the host's services with the hard state CRIT", offsets,
        ServiceListState{ServiceListState::Type::num_hard_crit}));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "num_services_hard_unknown",
        "The number of the host's services with the hard state UNKNOWN",
        offsets, ServiceListState{ServiceListState::Type::num_hard_unknown}));

    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "hard_state", "The effective hard state of this object",
        offsets, [](const row_type &row) { return row.hard_state(); }));
    table->addColumn(std::make_unique<BoolColumn<row_type>>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this object (-1/0/1)",
        offsets,
        [&core](const row_type &row) { return core.isPnpGraphPresent(row); }));

    // TODO CMK-23408
    const auto add_extension = [](std::filesystem::path p,
                                  const std::string &ext) {
        return p.replace_extension(p.extension().string() + ext);
    };
    const auto try_json = [&add_extension](const std::filesystem::path &p,
                                           const std::string &ext) {
        const auto json = add_extension(p, ".json" + ext);
        return std::filesystem::exists(json) ? json : add_extension(p, ext);
    };

    table->addColumn(std::make_unique<TimeColumn<row_type>>(
        prefix + "mk_inventory_last",
        "The timestamp of the last Check_MK HW/SW Inventory for this host. 0 means that no inventory data is present",
        offsets, [&core, &try_json](const row_type &row) {
            return mk_inventory_last(
                try_json(core.paths()->inventory_directory() / row.name(), ""));
        }));

    table->addColumn(std::make_unique<BlobColumn<row_type>>(
        prefix + "mk_inventory",
        "The file content of the Check_MK HW/SW Inventory", offsets,
        BlobFileReader<row_type>{[&core, &try_json](const row_type &row) {
            return try_json(core.paths()->inventory_directory() / row.name(),
                            "");
        }}));
    table->addColumn(std::make_unique<BlobColumn<row_type>>(
        prefix + "mk_inventory_gz",
        "The gzipped file content of the Check_MK HW/SW Inventory", offsets,
        BlobFileReader<row_type>{[&core, &try_json](const row_type &row) {
            return try_json(core.paths()->inventory_directory() / row.name(),
                            ".gz");
        }}));
    table->addColumn(std::make_unique<BlobColumn<row_type>>(
        prefix + "structured_status",
        "The file content of the structured status of the Check_MK HW/SW Inventory",
        offsets,
        BlobFileReader<row_type>{[&core, &try_json](const row_type &row) {
            return try_json(
                core.paths()->structured_status_directory() / row.name(), "");
        }}));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "mk_logwatch_files",
        "This list of logfiles with problems fetched via mk_logwatch", offsets,
        [&core](const row_type &row, const Column &col) {
            const auto logwatch_directory = core.paths()->logwatch_directory();
            auto dir = logwatch_directory.empty() || row.name().empty()
                           ? std::filesystem::path()
                           : logwatch_directory / pnp_cleanup(row.name());
            return getLogwatchList(dir, col);
        }));

    table->addDynamicColumn(std::make_unique<DynamicFileColumn<row_type>>(
        prefix + "mk_logwatch_file",
        "This contents of a logfile fetched via mk_logwatch", offsets,
        [&core](const row_type & /*row*/) {
            return core.paths()->logwatch_directory();
        },
        [](const std::string &args) { return std::filesystem::path{args}; }));

    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "staleness", "The staleness of this object", offsets,
        [](const row_type &row) { return row.staleness(); }));

    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "groups", "A list of all host groups this object is in",
        offsets, [](const row_type &row, const User &user) {
            std::vector<std::string> group_names;
            row.all_of_host_groups([&user, &group_names](const IHostGroup &g) {
                if (user.is_authorized_for_host_group(g)) {
                    group_names.emplace_back(g.name());
                }
                return true;
            });
            return group_names;
        }));
    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "contact_groups",
        "A list of all contact groups this object is in", offsets,
        [](const row_type &row) {
            std::vector<std::string> names;
            row.all_of_contact_groups([&names](const IContactGroup &g) {
                names.emplace_back(g.name());
                return true;
            });
            return names;
        }));

    table->addColumn(
        std::make_unique<ListColumn<row_type, ::column::service_list::Entry>>(
            prefix + "services", "A list of all services of the host", offsets,
            std::make_unique<ServiceListRenderer>(
                ServiceListRenderer::verbosity::none),
            getServices));
    table->addColumn(std::make_unique<
                     ListColumn<row_type, ::column::service_list::Entry>>(
        prefix + "services_with_state",
        "A list of all services of the host together with state and has_been_checked",
        offsets,
        std::make_unique<ServiceListRenderer>(
            ServiceListRenderer::verbosity::low),
        getServices));
    table->addColumn(std::make_unique<
                     ListColumn<row_type, ::column::service_list::Entry>>(
        prefix + "services_with_info",
        "A list of all services including detailed information about each service",
        offsets,
        std::make_unique<ServiceListRenderer>(
            ServiceListRenderer::verbosity::medium),
        getServices));
    table->addColumn(std::make_unique<
                     ListColumn<row_type, ::column::service_list::Entry>>(
        prefix + "services_with_fullstate",
        "A list of all services including full state information. The list of entries can grow in future versions.",
        offsets,
        std::make_unique<ServiceListRenderer>(
            ServiceListRenderer::verbosity::full),
        getServices));

    table->addColumn(std::make_unique<ListColumn<row_type>>(
        prefix + "metrics",
        "A list of all metrics of this object that historically existed",
        offsets, [&core](const row_type &row) { return core.metrics(row); }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "smartping_timeout",
        "Maximum expected time between two received packets in ms", offsets,
        [](const row_type &row) { return row.smartping_timeout(); }));
    table->addColumn(std::make_unique<DoubleColumn<row_type>>(
        prefix + "flappiness",
        "The current level of flappiness, this corresponds with the recent frequency of state changes",
        offsets, [](const row_type &row) { return row.flappiness(); }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "notification_postponement_reason",
        "reason for postponing the pending notification, empty if nothing is postponed",
        offsets, [](const row_type &row) {
            return row.notification_postponement_reason();
        }));
    table->addColumn(std::make_unique<IntColumn<row_type>>(
        prefix + "previous_hard_state",
        "Previous hard state (that hard state before the current/last hard state)",
        offsets,
        [](const row_type &row) { return row.previous_hard_state(); }));
}

void TableHosts::answerQuery(Query &query, const User &user,
                             const ICore &core) {
    auto *logger = core.loggerLivestatus();
    auto process = [&](const row_type &row) {
        return !user.is_authorized_for_host(row) ||
               query.processDataset(Row{&row});
    };

    // If we know the host, we use it directly.
    if (auto value = query.stringValueRestrictionFor("name")) {
        Debug(logger) << "using host name index with '" << *value << "'";
        if (const auto *h = core.find_host(*value)) {
            process(*h);
        }
        return;
    }

    // If we know the host group, we simply iterate over it.
    if (auto value = query.stringValueRestrictionFor("groups")) {
        Debug(logger) << "using host group index with '" << *value << "'";
        if (const auto *hg = core.find_hostgroup(*value)) {
            hg->all(process);
        }
        return;
    }

    // In the general case, we have to process all hosts.
    Debug(logger) << "using full table scan";
    core.all_of_hosts(process);
}

Row TableHosts::get(const std::string &primary_key, const ICore &core) const {
    // "name" is the primary key
    return Row{core.find_host(primary_key)};
}
