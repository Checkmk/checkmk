// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableServices.h"
#include <memory>
#include <optional>
#include <ostream>
#include <utility>
#include "AttributeListAsIntColumn.h"
#include "AttributeListColumn.h"
#include "Column.h"
#include "CommentColumn.h"
#include "ContactGroupsColumn.h"
#include "CustomTimeperiodColumn.h"
#include "CustomVarsDictColumn.h"
#include "CustomVarsExplicitColumn.h"
#include "CustomVarsNamesColumn.h"
#include "CustomVarsValuesColumn.h"
#include "DowntimeColumn.h"
#include "FixedIntColumn.h"
#include "Logger.h"
#include "MetricsColumn.h"
#include "MonitoringCore.h"
#include "OffsetDoubleColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetPerfdataColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetStringServiceMacroColumn.h"
#include "OffsetTimeColumn.h"
#include "Query.h"
#include "ServiceContactsColumn.h"
#include "ServiceGroupsColumn.h"
#include "ServiceSpecialDoubleColumn.h"
#include "ServiceSpecialIntColumn.h"
#include "StringUtils.h"
#include "TableHosts.h"
#include "TimeperiodColumn.h"
#include "auth.h"
#include "nagios.h"

extern service *service_list;

TableServices::TableServices(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", -1, true);
}

std::string TableServices::name() const { return "services"; }

std::string TableServices::namePrefix() const { return "service_"; }

// static
void TableServices::addColumns(Table *table, const std::string &prefix,
                               int indirect_offset, bool add_hosts) {
    // Es fehlen noch: double-Spalten, unsigned long spalten, etliche weniger
    // wichtige Spalten und die Servicegruppen.
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "description", "Description of the service (also used as key)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, description)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "display_name",
        "An optional display name (not used by Nagios standard web pages)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, display_name)));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "check_command", "Nagios command used for active checks",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, service_check_command)));
    table->addColumn(std::make_unique<OffsetStringServiceMacroColumn>(
        prefix + "check_command_expanded",
        "Nagios command used for active checks with the macros expanded",
        indirect_offset, -1, -1, table->core(),
        DANGEROUS_OFFSETOF(service, service_check_command)));
#else
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "check_command", "Nagios command used for active checks",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, check_command)));
    table->addColumn(std::make_unique<OffsetStringServiceMacroColumn>(
        prefix + "check_command_expanded",
        "Nagios command used for active checks with the macros expanded",
        indirect_offset, -1, -1, table->core(),
        DANGEROUS_OFFSETOF(service, check_command)));
#endif
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "event_handler", "Nagios command used as event handler",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, event_handler)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "plugin_output", "Output of the last check plugin",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, plugin_output)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "long_plugin_output",
        "Unabbreviated output of the last check plugin", indirect_offset, -1,
        -1, DANGEROUS_OFFSETOF(service, long_plugin_output)));
    table->addColumn(std::make_unique<OffsetPerfdataColumn>(
        prefix + "perf_data", "Performance data of the last check plugin",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, perf_data)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "notification_period",
        "The name of the notification period of the service. It this is empty, service problems are always notified.",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, notification_period)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "check_period",
        "The name of the check period of the service. It this is empty, the service is always checked.",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, check_period)));
    table->addColumn(std::make_unique<CustomVarsExplicitColumn>(
        prefix + "service_period",
        "The name of the service period of the service", indirect_offset, -1,
        -1, DANGEROUS_OFFSETOF(service, custom_variables), table->core(),
        "SERVICE_PERIOD"));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "notes", "Optional notes about the service", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, notes)));
    table->addColumn(std::make_unique<OffsetStringServiceMacroColumn>(
        prefix + "notes_expanded",
        "The notes with (the most important) macros expanded", indirect_offset,
        -1, -1, table->core(), DANGEROUS_OFFSETOF(service, notes)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "notes_url",
        "An optional URL for additional notes about the service",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, notes_url)));
    table->addColumn(std::make_unique<OffsetStringServiceMacroColumn>(
        prefix + "notes_url_expanded",
        "The notes_url with (the most important) macros expanded",
        indirect_offset, -1, -1, table->core(),
        DANGEROUS_OFFSETOF(service, notes_url)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "action_url",
        "An optional URL for actions or custom information about the service",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, action_url)));
    table->addColumn(std::make_unique<OffsetStringServiceMacroColumn>(
        prefix + "action_url_expanded",
        "The action_url with (the most important) macros expanded",
        indirect_offset, -1, -1, table->core(),
        DANGEROUS_OFFSETOF(service, action_url)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "icon_image",
        "The name of an image to be used as icon in the web interface",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, icon_image)));
    table->addColumn(std::make_unique<OffsetStringServiceMacroColumn>(
        prefix + "icon_image_expanded",
        "The icon_image with (the most important) macros expanded",
        indirect_offset, -1, -1, table->core(),
        DANGEROUS_OFFSETOF(service, icon_image)));
    table->addColumn(std::make_unique<OffsetStringColumn>(
        prefix + "icon_image_alt",
        "An alternative text for the icon_image for browsers not displaying icons",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, icon_image_alt)));

    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "initial_state", "The initial state of the service",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, initial_state)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "max_check_attempts", "The maximum number of check attempts",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, max_attempts)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "current_attempt", "The number of the current check attempt",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, current_attempt)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "state",
        "The current state of the service (0: OK, 1: WARN, 2: CRITICAL, 3: UNKNOWN)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, current_state)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "has_been_checked",
        "Whether the service already has been checked (0/1)", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, has_been_checked)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "last_state", "The last state of the service", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, last_state)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "last_hard_state", "The last hard state of the service",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, last_hard_state)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "state_type",
        "The type of the current state (0: soft, 1: hard)", indirect_offset, -1,
        -1, DANGEROUS_OFFSETOF(service, state_type)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "check_type",
        "The type of the last check (0: active, 1: passive)", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, check_type)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "acknowledged",
        "Whether the current service problem has been acknowledged (0/1)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, problem_has_been_acknowledged)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "acknowledgement_type",
        "The type of the acknownledgement (0: none, 1: normal, 2: sticky)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, acknowledgement_type)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)", indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, no_more_notifications)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_time_ok",
        "The last time the service was OK (Unix timestamp)", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, last_time_ok)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_time_warning",
        "The last time the service was in WARNING state (Unix timestamp)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, last_time_warning)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_time_critical",
        "The last time the service was CRITICAL (Unix timestamp)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, last_time_critical)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_time_unknown",
        "The last time the service was UNKNOWN (Unix timestamp)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, last_time_unknown)));

    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_check", "The time of the last check (Unix timestamp)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, last_check)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "next_check",
        "The scheduled time of the next check (Unix timestamp)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, next_check)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_notification",
        "The time of the last notification (Unix timestamp)", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, last_notification)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "next_notification",
        "The time of the next notification (Unix timestamp)", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, next_notification)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "current_notification_number",
        "The number of the current notification", indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, current_notification_number)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_state_change",
        "The time of the last state change - soft or hard (Unix timestamp)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, last_state_change)));
    table->addColumn(std::make_unique<OffsetTimeColumn>(
        prefix + "last_hard_state_change",
        "The time of the last hard state change (Unix timestamp)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, last_hard_state_change)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "scheduled_downtime_depth",
        "The number of scheduled downtimes the service is currently in",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, scheduled_downtime_depth)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "is_flapping", "Whether the service is flapping (0/1)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, is_flapping)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "checks_enabled",
        "Whether active checks are enabled for the service (0/1)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, checks_enabled)));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "accept_passive_checks",
        "Whether the service accepts passive checks (0/1)", indirect_offset, -1,
        -1, DANGEROUS_OFFSETOF(service, accept_passive_service_checks)));
#else
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "accept_passive_checks",
        "Whether the service accepts passive checks (0/1)", indirect_offset, -1,
        -1, DANGEROUS_OFFSETOF(service, accept_passive_checks)));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "event_handler_enabled",
        "Whether and event handler is activated for the service (0/1)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, event_handler_enabled)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "notifications_enabled",
        "Whether notifications are enabled for the service (0/1)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, notifications_enabled)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled for the service (0/1)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, process_performance_data)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "is_executing",
        "is there a service check currently running... (0/1)", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, is_executing)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "active_checks_enabled",
        "Whether active checks are enabled for the service (0/1)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, checks_enabled)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "check_options",
        "The current check option, forced, normal, freshness... (0/1)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, check_options)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled for the service (0/1)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, flap_detection_enabled)));
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "check_freshness",
        "Whether freshness checks are activated (0/1)", indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, check_freshness)));
#ifndef NAGIOS4
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "obsess_over_service",
        "Whether 'obsess_over_service' is enabled for the service (0/1)",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, obsess_over_service)));
#else
    table->addColumn(std::make_unique<OffsetIntColumn>(
        prefix + "obsess_over_service",
        "Whether 'obsess_over_service' is enabled for the service (0/1)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, obsess)));
#endif  // NAGIOS4
    table->addColumn(std::make_unique<AttributeListAsIntColumn>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, modified_attributes)));
    table->addColumn(std::make_unique<AttributeListColumn>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, modified_attributes)));
    table->addColumn(std::make_unique<ServiceSpecialIntColumn>(
        prefix + "hard_state",
        "The effective hard state of the service (eliminates a problem in hard_state)",
        indirect_offset, -1, -1, 0, table->core(),
        ServiceSpecialIntColumn::Type::real_hard_state));
    table->addColumn(std::make_unique<ServiceSpecialIntColumn>(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this service (0/1)",
        indirect_offset, -1, -1, 0, table->core(),
        ServiceSpecialIntColumn::Type::pnp_graph_present));
    table->addColumn(std::make_unique<ServiceSpecialDoubleColumn>(
        prefix + "staleness", "The staleness indicator for this service",
        indirect_offset, -1, -1, 0,
        ServiceSpecialDoubleColumn::Type::staleness));

    // columns of type double
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks of the service",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, check_interval)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a soft error",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, retry_interval)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "notification_interval",
        "Interval of periodic notification or 0 if its off", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, notification_interval)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "first_notification_delay",
        "Delay before the first notification", indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, first_notification_delay)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, low_flap_threshold)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, high_flap_threshold)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, latency)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "execution_time",
        "Time the service check needed for execution", indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, execution_time)));
    table->addColumn(std::make_unique<OffsetDoubleColumn>(
        prefix + "percent_state_change", "Percent state change",
        indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, percent_state_change)));

    table->addColumn(std::make_unique<TimeperiodColumn>(
        prefix + "in_check_period",
        "Whether the service is currently in its check period (0/1)",
        indirect_offset, DANGEROUS_OFFSETOF(service, check_period_ptr), -1, 0));
    table->addColumn(std::make_unique<CustomTimeperiodColumn>(
        prefix + "in_service_period",
        "Whether this service is currently in its service period (0/1)",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, custom_variables),
        table->core(), "SERVICE_PERIOD"));
    table->addColumn(std::make_unique<TimeperiodColumn>(
        prefix + "in_notification_period",
        "Whether the service is currently in its notification period (0/1)",
        indirect_offset, DANGEROUS_OFFSETOF(service, notification_period_ptr),
        -1, 0));

    table->addColumn(std::make_unique<ServiceContactsColumn>(
        prefix + "contacts",
        "A list of all contacts of the service, either direct or via a contact group",
        indirect_offset, -1, -1, 0));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes", "A list of all downtime ids of the service",
        indirect_offset, -1, -1, 0, table->core(), true,
        DowntimeColumn::info::none));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes_with_info",
        "A list of all downtimes of the service with id, author and comment",
        indirect_offset, -1, -1, 0, table->core(), true,
        DowntimeColumn::info::medium));
    table->addColumn(std::make_unique<DowntimeColumn>(
        prefix + "downtimes_with_extra_info",
        "A list of all downtimes of the service with id, author, comment, origin, entry_time, start_time, end_time, fixed, duration, recurring and is_pending",
        indirect_offset, -1, -1, 0, table->core(), true,
        DowntimeColumn::info::full));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments", "A list of all comment ids of the service",
        indirect_offset, -1, -1, 0, table->core(), true, false, false));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments_with_info",
        "A list of all comments of the service with id, author and comment",
        indirect_offset, -1, -1, 0, table->core(), true, true, false));
    table->addColumn(std::make_unique<CommentColumn>(
        prefix + "comments_with_extra_info",
        "A list of all comments of the service with id, author, comment, entry type and entry time",
        indirect_offset, -1, -1, 0, table->core(), true, true, true));

    if (add_hosts) {
        TableHosts::addColumns(table, "host_",
                               DANGEROUS_OFFSETOF(service, host_ptr), -1);
    }

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "custom_variable_names",
        "A list of the names of the custom variables of the service",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, custom_variables),
        table->core(), AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "custom_variable_values",
        "A list of the values of all custom variable of the service",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, custom_variables),
        table->core(), AttributeKind::custom_variables));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, custom_variables),
        table->core(), AttributeKind::custom_variables));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "tag_names", "A list of the names of the tags of the service",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, custom_variables),
        table->core(), AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "tag_values",
        "A list of the values of all tags of the service", indirect_offset, -1,
        -1, DANGEROUS_OFFSETOF(service, custom_variables), table->core(),
        AttributeKind::tags));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "tags", "A dictionary of the tags", indirect_offset, -1, -1,
        DANGEROUS_OFFSETOF(service, custom_variables), table->core(),
        AttributeKind::tags));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_names",
        "A list of the names of the labels of the service", indirect_offset, -1,
        -1, DANGEROUS_OFFSETOF(service, custom_variables), table->core(),
        AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_values",
        "A list of the values of all labels of the service", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, custom_variables), table->core(),
        AttributeKind::labels));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "labels", "A dictionary of the labels", indirect_offset, -1,
        -1, DANGEROUS_OFFSETOF(service, custom_variables), table->core(),
        AttributeKind::labels));

    table->addColumn(std::make_unique<CustomVarsNamesColumn>(
        prefix + "label_source_names",
        "A list of the names of the sources of the service", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, custom_variables), table->core(),
        AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsValuesColumn>(
        prefix + "label_source_values",
        "A list of the values of all sources of the service", indirect_offset,
        -1, -1, DANGEROUS_OFFSETOF(service, custom_variables), table->core(),
        AttributeKind::label_sources));
    table->addColumn(std::make_unique<CustomVarsDictColumn>(
        prefix + "label_sources", "A dictionary of the label sources",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, custom_variables),
        table->core(), AttributeKind::label_sources));

    table->addColumn(std::make_unique<ServiceGroupsColumn>(
        prefix + "groups", "A list of all service groups the service is in",
        indirect_offset, -1, -1, DANGEROUS_OFFSETOF(service, servicegroups_ptr),
        table->core()));
    table->addColumn(std::make_unique<ContactGroupsColumn>(
        prefix + "contact_groups",
        "A list of all contact groups this service is in", indirect_offset, -1,
        -1, DANGEROUS_OFFSETOF(service, contact_groups)));

    table->addColumn(std::make_unique<MetricsColumn>(
        prefix + "metrics",
        "A dummy column in order to be compatible with Check_MK Multisite",
        indirect_offset, -1, -1, 0));
    table->addColumn(std::make_unique<FixedIntColumn>(
        prefix + "cached_at",
        "A dummy column in order to be compatible with Check_MK Multisite", 0));
    table->addColumn(std::make_unique<FixedIntColumn>(
        prefix + "cache_interval",
        "A dummy column in order to be compatible with Check_MK Multisite", 0));
}

void TableServices::answerQuery(Query *query) {
    // do we know the host?
    if (auto value = query->stringValueRestrictionFor("host_name")) {
        Debug(logger()) << "using host name index with '" << *value << "'";
        // TODO(sp): Remove ugly cast.
        if (host *host =
                reinterpret_cast<::host *>(core()->find_host(*value))) {
            for (servicesmember *m = host->services; m != nullptr;
                 m = m->next) {
                if (!query->processDataset(Row(m->service_ptr))) {
                    break;
                }
            }
            return;
        }
    }

    // do we know the service group?
    if (auto value = query->stringValueRestrictionFor("groups")) {
        Debug(logger()) << "using service group index with '" << *value << "'";
        if (servicegroup *sg =
                find_servicegroup(const_cast<char *>(value->c_str()))) {
            for (servicesmember *m = sg->members; m != nullptr; m = m->next) {
                if (!query->processDataset(Row(m->service_ptr))) {
                    break;
                }
            }
        }
        return;
    }

    // do we know the host group?
    if (auto value = query->stringValueRestrictionFor("host_groups")) {
        Debug(logger()) << "using host group index with '" << *value << "'";
        if (hostgroup *hg =
                find_hostgroup(const_cast<char *>(value->c_str()))) {
            for (hostsmember *m = hg->members; m != nullptr; m = m->next) {
                for (servicesmember *smem = m->host_ptr->services;
                     smem != nullptr; smem = smem->next) {
                    if (!query->processDataset(Row(smem->service_ptr))) {
                        return;
                    }
                }
            }
        }
        return;
    }

    // no index -> iterator over *all* services
    Debug(logger()) << "using full table scan";
    for (service *svc = service_list; svc != nullptr; svc = svc->next) {
        if (!query->processDataset(Row(svc))) {
            break;
        }
    }
}

bool TableServices::isAuthorized(Row row, const contact *ctc) const {
    auto svc = rowData<service>(row);
    return is_authorized_for(core(), ctc, svc->host_ptr, svc);
}

Row TableServices::findObject(const std::string &objectspec) const {
    // The protocol proposes spaces as a separator between the host name and the
    // service description. That introduces the problem that host name
    // containing spaces will not work. For that reason we alternatively allow a
    // semicolon as a separator.
    auto semicolon = objectspec.find(';');
    auto host_and_desc =
        semicolon == std::string::npos
            ? mk::nextField(objectspec)
            : make_pair(mk::rstrip(objectspec.substr(0, semicolon)),
                        mk::rstrip(objectspec.substr(semicolon + 1)));
    return Row(core()->find_service(host_and_desc.first, host_and_desc.second));
}
