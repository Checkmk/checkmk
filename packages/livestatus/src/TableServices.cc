// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableServices.h"

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
#include "livestatus/DynamicRRDColumn.h"
#include "livestatus/ICore.h"
#include "livestatus/IntColumn.h"
#include "livestatus/Interface.h"
#include "livestatus/ListColumn.h"
#include "livestatus/Logger.h"
#include "livestatus/MapUtils.h"
#include "livestatus/Query.h"
#include "livestatus/RRDColumn.h"
#include "livestatus/StringColumn.h"
#include "livestatus/StringUtils.h"
#include "livestatus/TableHosts.h"
#include "livestatus/TimeColumn.h"
#include "livestatus/User.h"

using namespace std::string_literals;

TableServices::TableServices(ICore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{}, AddHosts::yes, LockComments::yes,
               LockDowntimes::yes);
}

std::string TableServices::name() const { return "services"; }

std::string TableServices::namePrefix() const { return "service_"; }

// static
void TableServices::addColumns(Table *table, const std::string &prefix,
                               const ColumnOffsets &offsets, AddHosts add_hosts,
                               LockComments lock_comments,
                               LockDowntimes lock_downtimes) {
    auto *mc = table->core();
    // Es fehlen noch: double-Spalten, unsigned long spalten, etliche weniger
    // wichtige Spalten und die Servicegruppen.
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "description", "Service description", offsets,
        [](const IService &r) { return r.description(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "display_name", "Optional display name", offsets,
        [](const IService &r) { return r.display_name(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "check_command", "Logical command name for active checks",
        offsets, [](const IService &r) { return r.check_command(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "check_command_expanded",
        "Logical command name for active checks, with macros expanded", offsets,
        [](const IService &r) { return r.check_command_expanded(); }));
    table->addColumn(std::make_unique<BlobColumn<IService>>(
        prefix + "robotmk_last_log", "The file content of the Robotmk log",
        offsets,
        BlobFileReader<IService>{
            [mc]() { return mc->paths()->robotmk_html_log_directory(); },
            [](const IService &r) {
                return r.robotmk_dir() / "suite_last_log.html";
            }}));
    table->addColumn(std::make_unique<BlobColumn<IService>>(
        prefix + "robotmk_last_log_gz",
        "The gzipped file content of the Robotmk log", offsets,
        BlobFileReader<IService>{
            [mc]() { return mc->paths()->robotmk_html_log_directory(); },
            [](const IService &r) {
                return r.robotmk_dir() / "suite_last_log.html.gz";
            }}));
    table->addColumn(std::make_unique<BlobColumn<IService>>(
        prefix + "robotmk_last_error_log",
        "The file content of the Robotmk error log", offsets,
        BlobFileReader<IService>{
            [mc]() { return mc->paths()->robotmk_html_log_directory(); },
            [](const IService &r) {
                return r.robotmk_dir() / "suite_last_error_log.html";
            }}));
    table->addColumn(std::make_unique<BlobColumn<IService>>(
        prefix + "robotmk_last_error_log_gz",
        "The gzipped file content of the Robotmk error log", offsets,
        BlobFileReader<IService>{
            [mc]() { return mc->paths()->robotmk_html_log_directory(); },
            [](const IService &r) {
                return r.robotmk_dir() / "suite_last_error_log.html.gz";
            }}));

    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "event_handler", "Command used as event handler", offsets,
        [](const IService &r) { return r.event_handler(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "plugin_output", "Output of the last check", offsets,
        [](const IService &r) { return r.plugin_output(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "long_plugin_output", "Long (extra) output of the last check",
        offsets, [](const IService &r) { return r.long_plugin_output(); }));
    table->addColumn(std::make_unique<StringColumnPerfData<IService>>(
        prefix + "perf_data", "Optional performance data of the last check",
        offsets, [](const IService &r) { return r.perf_data(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "notification_period",
        "Time period in which problems of this object will be notified. If empty then notification will be always",
        offsets, [](const IService &r) { return r.notificationPeriodName(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "check_period",
        "Time period in which this object will be checked. If empty then the check will always be executed.",
        offsets, [](const IService &r) { return r.check_period(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "service_period",
        "Time period during which the object is expected to be available",
        offsets, [](const IService &r) { return r.servicePeriodName(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "notes",
        "Optional notes for this object, with macros not expanded", offsets,
        [](const IService &r) { return r.notes(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "notes_expanded",
        "The same as notes, but with the most important macros expanded",
        offsets, [](const IService &r) { return r.notes_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "notes_url",
        "An optional URL with further information about the object", offsets,
        [](const IService &r) { return r.notes_url(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "notes_url_expanded",
        "Same es notes_url, but with the most important macros expanded",
        offsets, [](const IService &r) { return r.notes_url_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "action_url",
        "An optional URL to custom actions or information about this host",
        offsets, [](const IService &r) { return r.action_url(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "action_url_expanded",
        "The same as action_url, but with the most important macros expanded",
        offsets, [](const IService &r) { return r.action_url_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "icon_image",
        "The name of an image file to be used in the web pages", offsets,
        [](const IService &r) { return r.icon_image(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "icon_image_expanded",
        "The same as icon_image, but with the most important macros expanded",
        offsets, [](const IService &r) { return r.icon_image_expanded(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "icon_image_alt", "Alternative text for the icon_image",
        offsets, [](const IService &r) { return r.icon_image_alt(); }));

    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "initial_state", "Initial state", offsets,
        [](const IService &r) { return r.initial_state(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "max_check_attempts",
        "Maximum attempts for active checks before a hard state", offsets,
        [](const IService &r) { return r.max_check_attempts(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "current_attempt", "Number of the current check attempts",
        offsets, [](const IService &r) { return r.current_attempt(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "state",
        "The current state of the object, for hosts: 0/1/2 for UP/DOWN/UNREACH, for services: 0/1/2/3 for OK/WARN/CRIT/UNKNOWN",
        offsets, [](const IService &r) { return r.current_state(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "has_been_checked",
        "Whether a check has already been executed (0/1)", offsets,
        [](const IService &r) { return r.has_been_checked(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "last_state", "State before last state change", offsets,
        [](const IService &r) { return r.last_state(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "last_hard_state", "Last hard state", offsets,
        [](const IService &r) { return r.last_hard_state(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "state_type", "Type of the current state (0: soft, 1: hard)",
        offsets, [](const IService &r) { return r.state_type(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "check_type", "Type of check (0: active, 1: passive)", offsets,
        [](const IService &r) { return r.check_type(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "acknowledged",
        "Whether the current problem has been acknowledged (0/1)", offsets,
        [](const IService &r) { return r.problem_has_been_acknowledged(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "acknowledgement_type",
        "Type of acknowledgement (0: none, 1: normal, 2: sticky)", offsets,
        [](const IService &r) { return r.acknowledgement_type(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)", offsets,
        [](const IService &r) { return r.no_more_notifications(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "last_time_ok",
        "The last time the service was OK (Unix timestamp)", offsets,
        [](const IService &r) { return r.last_time_ok(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "last_time_warning",
        "The last time the service was WARN (Unix timestamp)", offsets,
        [](const IService &r) { return r.last_time_warning(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "last_time_critical",
        "The last time the service was CRIT (Unix timestamp)", offsets,
        [](const IService &r) { return r.last_time_critical(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "last_time_unknown",
        "The last time the service was UNKNOWN (Unix timestamp)", offsets,
        [](const IService &r) { return r.last_time_unknown(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "last_check", "Time of the last check (Unix timestamp)",
        offsets, [](const IService &r) { return r.last_check(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "next_check",
        "Scheduled time for the next check (Unix timestamp)", offsets,
        [](const IService &r) { return r.next_check(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "last_notification",
        "Time of the last notification (Unix timestamp)", offsets,
        [](const IService &r) { return r.last_notification(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "next_notification",
        "Time of the next notification (Unix timestamp)", offsets,
        [](const IService &r) { return r.next_notification(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "current_notification_number",
        "Number of the current notification", offsets,
        [](const IService &r) { return r.current_notification_number(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "last_state_change",
        "Time of the last state change - soft or hard (Unix timestamp)",
        offsets, [](const IService &r) { return r.last_state_change(); }));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "last_hard_state_change",
        "Time of the last hard state change - soft or hard (Unix timestamp)",
        offsets, [](const IService &r) { return r.last_hard_state_change(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "scheduled_downtime_depth",
        "The number of downtimes this object is currently in", offsets,
        [](const IService &r) { return r.scheduled_downtime_depth(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "is_flapping", "Whether the state is flapping (0/1)", offsets,
        [](const IService &r) { return r.is_flapping(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "checks_enabled",
        "Whether checks of the object are enabled (0/1)", offsets,
        [](const IService &r) { return r.checks_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "accept_passive_checks",
        "Whether passive host checks are accepted (0/1)", offsets,
        [](const IService &r) { return r.accept_passive_checks(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "event_handler_enabled",
        "Whether event handling is enabled (0/1)", offsets,
        [](const IService &r) { return r.event_handler_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "notifications_enabled",
        "Whether notifications of the host are enabled (0/1)", offsets,
        [](const IService &r) { return r.notifications_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled (0/1)", offsets,
        [](const IService &r) { return r.process_performance_data(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "is_executing", "is there a check currently running (0/1)",
        offsets, [](const IService &r) { return r.is_executing(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "active_checks_enabled",
        "Whether active checks of the object are enabled (0/1)", offsets,
        [](const IService &r) { return r.active_checks_enabled(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness (0-2)", offsets,
        [](const IService &r) { return r.check_options(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled (0/1)", offsets,
        [](const IService &r) { return r.flap_detection_enabled(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "check_freshness",
        "Whether freshness checks are enabled (0/1)", offsets,
        [](const IService &r) { return r.check_freshness(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "obsess_over_service",
        "The current obsess_over_service setting (0/1)", offsets,
        [](const IService &r) { return r.obsess_over_service(); }));
    table->addColumn(std::make_unique<AttributeBitmaskColumn<IService>>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified", offsets,
        [](const IService &r) { return r.modified_attributes(); }));
    table->addColumn(std::make_unique<AttributeListColumn<
                         IService, column::attribute_list::AttributeBit>>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", offsets, [](const IService &r) {
            return column::attribute_list::encode(r.modified_attributes());
        }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "hard_state", "The effective hard state of this object",
        offsets, [](const IService &r) { return r.hard_state(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this object (-1/0/1)",
        offsets, [mc](const IService &r) { return mc->isPnpGraphPresent(r); }));

    // columns of type double
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "staleness", "The staleness of this object", offsets,
        [](const IService &r) { return r.staleness(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks",
        offsets, [](const IService &r) { return r.check_interval(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a soft error",
        offsets, [](const IService &r) { return r.retry_interval(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "notification_interval",
        "Interval of periodic notification in minutes or 0 if its off", offsets,
        [](const IService &r) { return r.notification_interval(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "first_notification_delay",
        "Delay before the first notification", offsets,
        [](const IService &r) { return r.first_notification_delay(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        offsets, [](const IService &r) { return r.low_flap_threshold(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        offsets, [](const IService &r) { return r.high_flap_threshold(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        offsets, [](const IService &r) { return r.latency(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "execution_time", "Time the check needed for execution",
        offsets, [](const IService &r) { return r.execution_time(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "percent_state_change", "Percent state change", offsets,
        [](const IService &r) { return r.percent_state_change(); }));

    table->addColumn(std::make_unique<BoolColumn<IService, true>>(
        prefix + "in_check_period",
        "Whether this object is currently in its check period (0/1)", offsets,
        [](const IService &r) { return r.in_check_period(); }));
    table->addColumn(std::make_unique<BoolColumn<IService, true>>(
        prefix + "in_service_period",
        "Whether this object is currently in its service period (0/1)", offsets,
        [](const IService &r) { return r.in_service_period(); }));
    table->addColumn(std::make_unique<BoolColumn<IService, true>>(
        prefix + "in_notification_period",
        "Whether this object is currently in its notification period (0/1)",
        offsets, [](const IService &r) { return r.in_notification_period(); }));

    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "contacts", "A list of all contacts of this object", offsets,
        [](const IService &r) { return r.contacts(); }));

    auto get_downtimes = [mc, lock_downtimes](const IService &s) {
        return lock_downtimes == LockDowntimes::yes ? mc->downtimes(s)
                                                    : mc->downtimes_unlocked(s);
    };
    table->addColumn(std::make_unique<
                     ListColumn<IService, std::unique_ptr<const IDowntime>>>(
        prefix + "downtimes",
        "A list of the ids of all scheduled downtimes of this object", offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::none),
        get_downtimes));
    table->addColumn(std::make_unique<
                     ListColumn<IService, std::unique_ptr<const IDowntime>>>(
        prefix + "downtimes_with_info",
        "A list of the scheduled downtimes with id, author and comment",
        offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::medium),
        get_downtimes));
    table->addColumn(std::make_unique<
                     ListColumn<IService, std::unique_ptr<const IDowntime>>>(
        prefix + "downtimes_with_extra_info",
        "A list of the scheduled downtimes with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending",
        offsets,
        std::make_unique<DowntimeRenderer>(DowntimeRenderer::verbosity::full),
        get_downtimes));

    auto get_comments = [mc, lock_comments](const IService &s) {
        return lock_comments == LockComments::yes ? mc->comments(s)
                                                  : mc->comments_unlocked(s);
    };
    table->addColumn(
        std::make_unique<ListColumn<IService, std::unique_ptr<const IComment>>>(
            prefix + "comments", "A list of the ids of all comments", offsets,
            std::make_unique<CommentRenderer>(CommentRenderer::verbosity::none),
            get_comments));
    table->addColumn(
        std::make_unique<ListColumn<IService, std::unique_ptr<const IComment>>>(
            prefix + "comments_with_info",
            "A list of all comments with id, author and comment", offsets,
            std::make_unique<CommentRenderer>(
                CommentRenderer::verbosity::medium),
            get_comments));
    table->addColumn(std::make_unique<
                     ListColumn<IService, std::unique_ptr<const IComment>>>(
        prefix + "comments_with_extra_info",
        "A list of all comments with id, author, comment, entry type and entry time",
        offsets,
        std::make_unique<CommentRenderer>(CommentRenderer::verbosity::full),
        get_comments));

    if (add_hosts == AddHosts::yes) {
        TableHosts::addColumns(table, "host_", offsets.add([](Row r) {
            return &r.rawData<IService>()->host();
        }),
                               LockComments::yes, LockDowntimes::yes);
    }

    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables", offsets,
        [](const IService &r) {
            return mk::map_keys(r.attributes(AttributeKind::custom_variables));
        }));
    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "custom_variable_values",
        "A list of the values of the custom variables", offsets,
        [](const IService &r) {
            return mk::map_values(
                r.attributes(AttributeKind::custom_variables));
        }));
    table->addColumn(std::make_unique<DictColumn<IService>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets, [](const IService &r) {
            return r.attributes(AttributeKind::custom_variables);
        }));

    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "tag_names", "A list of the names of the tags", offsets,
        [](const IService &r) {
            return mk::map_keys(r.attributes(AttributeKind::tags));
        }));
    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "tag_values", "A list of the values of the tags", offsets,
        [](const IService &r) {
            return mk::map_values(r.attributes(AttributeKind::tags));
        }));
    table->addColumn(std::make_unique<DictColumn<IService>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        [](const IService &r) { return r.attributes(AttributeKind::tags); }));

    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "label_names", "A list of the names of the labels", offsets,
        [](const IService &r) {
            return mk::map_keys(r.attributes(AttributeKind::labels));
        }));
    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "label_values", "A list of the values of the labels", offsets,
        [](const IService &r) {
            return mk::map_values(r.attributes(AttributeKind::labels));
        }));
    table->addColumn(std::make_unique<DictColumn<IService>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        [](const IService &r) { return r.attributes(AttributeKind::labels); }));

    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "label_source_names",
        "A list of the names of the label sources", offsets,
        [](const IService &r) {
            return mk::map_keys(r.attributes(AttributeKind::label_sources));
        }));
    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "label_source_values",
        "A list of the values of the label sources", offsets,
        [](const IService &r) {
            return mk::map_values(r.attributes(AttributeKind::label_sources));
        }));
    table->addColumn(std::make_unique<DictColumn<IService>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        [](const IService &r) {
            return r.attributes(AttributeKind::label_sources);
        }));

    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "groups", "A list of all service groups this object is in",
        offsets, [](const IService &r, const User &user) {
            std::vector<std::string> group_names;
            r.all_of_service_groups(
                [&user, &group_names](const IServiceGroup &g) {
                    if (user.is_authorized_for_service_group(g)) {
                        group_names.emplace_back(g.name());
                    }
                    return true;
                });
            return group_names;
        }));

    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "contact_groups",
        "A list of all contact groups this object is in", offsets,
        [](const IService &r) {
            std::vector<std::string> group_names;
            r.all_of_contact_groups([&group_names](const IContactGroup &g) {
                group_names.emplace_back(g.name());
                return true;
            });
            return group_names;
        }));

    table->addColumn(std::make_unique<ListColumn<IService>>(
        prefix + "metrics",
        "A list of all metrics of this object that historically existed",
        offsets,
        [mc](const IService &r) { return mc->metrics(r, mc->loggerRRD()); }));
    table->addDynamicColumn(std::make_unique<DynamicRRDColumn<ListColumn<
                                IService, RRDDataMaker::value_type>>>(
        prefix + "rrddata",
        "RRD metrics data of this object. This is a column with parameters: rrddata:COLUMN_TITLE:VARNAME:FROM_TIME:UNTIL_TIME:RESOLUTION",
        table->core(), offsets));
    table->addColumn(std::make_unique<TimeColumn<IService>>(
        prefix + "cached_at",
        "For checks that base on cached agent data the time when this data was created. 0 for other services.",
        offsets, [](const IService &r) { return r.cached_at(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "cache_interval",
        "For checks that base on cached agent data the interval in that this cache is recreated. 0 for other services.",
        offsets, [](const IService &r) { return r.cache_interval(); }));

    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "in_passive_check_period",
        "Whether this service is currently in its passive check period (0/1)",
        offsets,
        [](const IService &r) { return r.in_passive_check_period(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "passive_check_period",
        "Time period in which this (passive) service will be checked.", offsets,
        [](const IService &r) { return r.passive_check_period(); }));
    table->addColumn(std::make_unique<DoubleColumn<IService>>(
        prefix + "flappiness",
        "The current level of flappiness, this corresponds with the recent frequency of state changes",
        offsets, [](const IService &r) { return r.flappiness(); }));
    table->addColumn(std::make_unique<StringColumn<IService>>(
        prefix + "notification_postponement_reason",
        "reason for postponing the pending notification, empty if nothing is postponed",
        offsets, [](const IService &r) {
            return r.notification_postponement_reason();
        }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "previous_hard_state",
        "Previous hard state (that hard state before the current/last hard state)",
        offsets, [](const IService &r) { return r.previous_hard_state(); }));
    table->addColumn(std::make_unique<IntColumn<IService>>(
        prefix + "pending_flex_downtime",
        "Number of pending flexible downtimes", offsets,
        [](const IService &r) { return r.pending_flex_downtime(); }));
    table->addColumn(std::make_unique<BoolColumn<IService>>(
        prefix + "check_flapping_recovery_notification",
        "Whether to check to send a recovery notification when flapping stops (0/1)",
        offsets, [](const IService &r) {
            return r.check_flapping_recovery_notification();
        }));
}

void TableServices::answerQuery(Query &query, const User &user) {
    auto process = [&](const IService &s) {
        return !user.is_authorized_for_service(s) ||
               query.processDataset(Row{&s});
    };

    // If we know the host, we use it directly.
    if (auto value = query.stringValueRestrictionFor("host_name")) {
        Debug(logger()) << "using host name index with '" << *value << "'";
        if (const auto *hst = core()->find_host(*value)) {
            hst->all_of_services(
                [&process](const IService &s) { return process(s); });
        }
        return;
    }

    // If we know the service group, we simply iterate over it.
    if (auto value = query.stringValueRestrictionFor("groups")) {
        Debug(logger()) << "using service group index with '" << *value << "'";
        if (const auto *sg = core()->find_servicegroup(*value)) {
            sg->all([&process](const IService &s) { return process(s); });
        }
        return;
    }

    // If we know the host group, we simply iterate over it.
    if (auto value = query.stringValueRestrictionFor("host_groups")) {
        Debug(logger()) << "using host group index with '" << *value << "'";
        if (const auto *hg = core()->find_hostgroup(*value)) {
            hg->all([&process](const IHost &h) {
                return h.all_of_services(
                    [&process](const IService &s) { return process(s); });
            });
        }
        return;
    }

    // In the general case, we have to process all services.
    Debug(logger()) << "using full table scan";
    core()->all_of_services(
        [&process](const IService &s) { return process(s); });
}

Row TableServices::get(const std::string &primary_key) const {
    // "host_name;description" is the primary key
    const auto &[host_name, description] = mk::splitCompositeKey2(primary_key);
    return Row{core()->find_service(host_name, description)};
}
