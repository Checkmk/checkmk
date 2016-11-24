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
#include "AttributeListAsIntColumn.h"
#include "AttributeListColumn.h"
#include "ContactGroupsColumn.h"
#include "CustomTimeperiodColumn.h"
#include "CustomVarsDictColumn.h"
#include "CustomVarsExplicitColumn.h"
#include "CustomVarsNamesColumn.h"
#include "CustomVarsValuesColumn.h"
#include "DownCommColumn.h"
#include "FixedIntColumn.h"
#include "MetricsColumn.h"
#include "MonitoringCore.h"
#include "OffsetDoubleColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetStringColumn.h"
#include "OffsetStringServiceMacroColumn.h"
#include "OffsetTimeColumn.h"
#include "OffsetTimeperiodColumn.h"
#include "Query.h"
#include "ServiceContactsColumn.h"
#include "ServiceGroupsColumn.h"
#include "ServiceSpecialDoubleColumn.h"
#include "ServiceSpecialIntColumn.h"
#include "TableHosts.h"
#include "WorldNagios.h"
#include "auth.h"

extern service *service_list;

using std::string;

TableServices::TableServices(const DowntimesOrComments &downtimes_holder,
                             const DowntimesOrComments &comments_holder,
                             MonitoringCore *core)
    : Table(core->loggerLivestatus()) {
    addColumns(this, "", -1, true, downtimes_holder, comments_holder, core);
}

string TableServices::name() const { return "services"; }

string TableServices::namePrefix() const { return "service_"; }

// static
void TableServices::addColumns(Table *table, const string &prefix,
                               int indirect_offset, bool add_hosts,
                               const DowntimesOrComments &downtimes_holder,
                               const DowntimesOrComments &comments_holder,
                               MonitoringCore *core) {
    // Es fehlen noch: double-Spalten, unsigned long spalten, etliche weniger
    // wichtige Spalten und die Servicegruppen.

    service svc;
    const char *ref = reinterpret_cast<const char *>(&svc);
    table->addColumn(new OffsetStringColumn(
        prefix + "description", "Description of the service (also used as key)",
        reinterpret_cast<char *>(&svc.description) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "display_name",
        "An optional display name (not used by Nagios standard web pages)",
        reinterpret_cast<char *>(&svc.display_name) - ref, indirect_offset));
#ifndef NAGIOS4
    table->addColumn(new OffsetStringColumn(
        prefix + "check_command", "Nagios command used for active checks",
        reinterpret_cast<char *>(&svc.service_check_command) - ref,
        indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(
        prefix + "check_command_expanded",
        "Nagios command used for active checks with the macros expanded",
        reinterpret_cast<char *>(&svc.service_check_command) - ref,
        indirect_offset));
#else
    table->addColumn(new OffsetStringColumn(
        prefix + "check_command", "Nagios command used for active checks",
        (char *)(&svc.check_command) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(
        prefix + "check_command_expanded",
        "Nagios command used for active checks with the macros expanded",
        (char *)(&svc.check_command) - ref, indirect_offset));
#endif
    table->addColumn(new OffsetStringColumn(
        prefix + "event_handler", "Nagios command used as event handler",
        reinterpret_cast<char *>(&svc.event_handler) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "plugin_output", "Output of the last check plugin",
        reinterpret_cast<char *>(&svc.plugin_output) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "long_plugin_output",
        "Unabbreviated output of the last check plugin",
        reinterpret_cast<char *>(&svc.long_plugin_output) - ref,
        indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "perf_data", "Performance data of the last check plugin",
        reinterpret_cast<char *>(&svc.perf_data) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "notification_period",
        "The name of the notification period of the service. It this is empty, "
        "service problems are always notified.",
        reinterpret_cast<char *>(&svc.notification_period) - ref,
        indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "check_period",
        "The name of the check period of the service. It this is empty, the "
        "service is always checked.",
        reinterpret_cast<char *>(&svc.check_period) - ref, indirect_offset));
    table->addColumn(new CustomVarsExplicitColumn(
        prefix + "service_period",
        "The name of the service period of the service",
        reinterpret_cast<char *>(&svc.custom_variables) - ref, indirect_offset,
        "SERVICE_PERIOD"));
    table->addColumn(new OffsetStringColumn(
        prefix + "notes", "Optional notes about the service",
        reinterpret_cast<char *>(&svc.notes) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(
        prefix + "notes_expanded",
        "The notes with (the most important) macros expanded",
        reinterpret_cast<char *>(&svc.notes) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "notes_url",
        "An optional URL for additional notes about the service",
        reinterpret_cast<char *>(&svc.notes_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(
        prefix + "notes_url_expanded",
        "The notes_url with (the most important) macros expanded",
        reinterpret_cast<char *>(&svc.notes_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "action_url",
        "An optional URL for actions or custom information about the service",
        reinterpret_cast<char *>(&svc.action_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(
        prefix + "action_url_expanded",
        "The action_url with (the most important) macros expanded",
        reinterpret_cast<char *>(&svc.action_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "icon_image",
        "The name of an image to be used as icon in the web interface",
        reinterpret_cast<char *>(&svc.icon_image) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(
        prefix + "icon_image_expanded",
        "The icon_image with (the most important) macros expanded",
        reinterpret_cast<char *>(&svc.icon_image) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "icon_image_alt",
        "An alternative text for the icon_image for browsers not displaying "
        "icons",
        reinterpret_cast<char *>(&svc.icon_image_alt) - ref, indirect_offset));

    table->addColumn(new OffsetIntColumn(
        prefix + "initial_state", "The initial state of the service",
        reinterpret_cast<char *>(&svc.initial_state) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "max_check_attempts", "The maximum number of check attempts",
        reinterpret_cast<char *>(&svc.max_attempts) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "current_attempt", "The number of the current check attempt",
        reinterpret_cast<char *>(&svc.current_attempt) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "state",
        "The current state of the service (0: OK, 1: WARN, "
        "2: CRITICAL, 3: UNKNOWN)",
        reinterpret_cast<char *>(&svc.current_state) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "has_been_checked",
        "Whether the service already has been checked (0/1)",
        reinterpret_cast<char *>(&svc.has_been_checked) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "last_state", "The last state of the service",
        reinterpret_cast<char *>(&svc.last_state) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "last_hard_state", "The last hard state of the service",
        reinterpret_cast<char *>(&svc.last_hard_state) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "state_type",
        "The type of the current state (0: soft, 1: hard)",
        reinterpret_cast<char *>(&svc.state_type) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "check_type",
        "The type of the last check (0: active, 1: passive)",
        reinterpret_cast<char *>(&svc.check_type) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "acknowledged",
        "Whether the current service problem has been acknowledged (0/1)",
        reinterpret_cast<char *>(&svc.problem_has_been_acknowledged) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "acknowledgement_type",
        "The type of the acknownledgement (0: none, 1: normal, 2: sticky)",
        reinterpret_cast<char *>(&svc.acknowledgement_type) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "no_more_notifications",
        "Whether to stop sending notifications (0/1)",
        reinterpret_cast<char *>(&svc.no_more_notifications) - ref,
        indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "last_state_change",
        "The time of the last state change (Unix timestamp)",
        reinterpret_cast<char *>(&svc.last_state_change) - ref,
        indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "last_time_ok",
        "The last time the service was OK (Unix timestamp)",
        reinterpret_cast<char *>(&svc.last_time_ok) - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "last_time_warning",
        "The last time the service was in WARNING state (Unix timestamp)",
        reinterpret_cast<char *>(&svc.last_time_warning) - ref,
        indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "last_time_critical",
        "The last time the service was CRITICAL (Unix timestamp)",
        reinterpret_cast<char *>(&svc.last_time_critical) - ref,
        indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "last_time_unknown",
        "The last time the service was UNKNOWN (Unix timestamp)",
        reinterpret_cast<char *>(&svc.last_time_unknown) - ref,
        indirect_offset));

    table->addColumn(new OffsetTimeColumn(
        prefix + "last_check", "The time of the last check (Unix timestamp)",
        reinterpret_cast<char *>(&svc.last_check) - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "next_check",
        "The scheduled time of the next check (Unix timestamp)",
        reinterpret_cast<char *>(&svc.next_check) - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "last_notification",
        "The time of the last notification (Unix timestamp)",
        reinterpret_cast<char *>(&svc.last_notification) - ref,
        indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "next_notification",
        "The time of the next notification (Unix timestamp)",
        reinterpret_cast<char *>(&svc.next_notification) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "current_notification_number",
        "The number of the current notification",
        reinterpret_cast<char *>(&svc.current_notification_number) - ref,
        indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "last_state_change",
        "The time of the last state change - soft or hard (Unix timestamp)",
        reinterpret_cast<char *>(&svc.last_state_change) - ref,
        indirect_offset));
    table->addColumn(new OffsetTimeColumn(
        prefix + "last_hard_state_change",
        "The time of the last hard state change (Unix timestamp)",
        reinterpret_cast<char *>(&svc.last_hard_state_change) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "scheduled_downtime_depth",
        "The number of scheduled downtimes the service is currently in",
        reinterpret_cast<char *>(&svc.scheduled_downtime_depth) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "is_flapping", "Whether the service is flapping (0/1)",
        reinterpret_cast<char *>(&svc.is_flapping) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "checks_enabled",
        "Whether active checks are enabled for the service (0/1)",
        reinterpret_cast<char *>(&svc.checks_enabled) - ref, indirect_offset));
#ifndef NAGIOS4
    table->addColumn(new OffsetIntColumn(
        prefix + "accept_passive_checks",
        "Whether the service accepts passive checks (0/1)",
        reinterpret_cast<char *>(&svc.accept_passive_service_checks) - ref,
        indirect_offset));
#else
    table->addColumn(new OffsetIntColumn(
        prefix + "accept_passive_checks",
        "Whether the service accepts passive checks (0/1)",
        (char *)(&svc.accept_passive_checks) - ref, indirect_offset));
#endif  // NAGIOS4
    table->addColumn(new OffsetIntColumn(
        prefix + "event_handler_enabled",
        "Whether and event handler is activated for the service (0/1)",
        reinterpret_cast<char *>(&svc.event_handler_enabled) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "notifications_enabled",
        "Whether notifications are enabled for the service (0/1)",
        reinterpret_cast<char *>(&svc.notifications_enabled) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "process_performance_data",
        "Whether processing of performance data is enabled for the service "
        "(0/1)",
        reinterpret_cast<char *>(&svc.process_performance_data) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "is_executing",
        "is there a service check currently running... (0/1)",
        reinterpret_cast<char *>(&svc.is_executing) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "active_checks_enabled",
        "Whether active checks are enabled for the service (0/1)",
        reinterpret_cast<char *>(&svc.checks_enabled) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "check_options",
        "The current check option, forced, normal, freshness... (0/1)",
        reinterpret_cast<char *>(&svc.check_options) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "flap_detection_enabled",
        "Whether flap detection is enabled for the service (0/1)",
        reinterpret_cast<char *>(&svc.flap_detection_enabled) - ref,
        indirect_offset));
    table->addColumn(new OffsetIntColumn(
        prefix + "check_freshness",
        "Whether freshness checks are activated (0/1)",
        reinterpret_cast<char *>(&svc.check_freshness) - ref, indirect_offset));
#ifndef NAGIOS4
    table->addColumn(new OffsetIntColumn(
        prefix + "obsess_over_service",
        "Whether 'obsess_over_service' is enabled for the service (0/1)",
        reinterpret_cast<char *>(&svc.obsess_over_service) - ref,
        indirect_offset));
#else
    table->addColumn(new OffsetIntColumn(
        prefix + "obsess_over_service",
        "Whether 'obsess_over_service' is enabled for the service (0/1)",
        (char *)(&svc.obsess) - ref, indirect_offset));
#endif  // NAGIOS4
    table->addColumn(new AttributeListAsIntColumn(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified",
        reinterpret_cast<char *>(&svc.modified_attributes) - ref,
        indirect_offset, -1, -1));
    table->addColumn(new AttributeListColumn(
        prefix + "modified_attributes_list",
        "A list of all modified attributes",
        reinterpret_cast<char *>(&svc.modified_attributes) - ref,
        indirect_offset, -1, -1));
    table->addColumn(new ServiceSpecialIntColumn(
        prefix + "pnpgraph_present",
        "Whether there is a PNP4Nagios graph present for this service (0/1)",
        SSIC_PNP_GRAPH_PRESENT, indirect_offset));
    table->addColumn(new ServiceSpecialDoubleColumn(
        prefix + "staleness", "The staleness indicator for this service",
        SSDC_STALENESS, indirect_offset));

    // columns of type double
    table->addColumn(new OffsetDoubleColumn(
        prefix + "check_interval",
        "Number of basic interval lengths between two scheduled checks of the "
        "service",
        reinterpret_cast<char *>(&svc.check_interval) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(
        prefix + "retry_interval",
        "Number of basic interval lengths between checks when retrying after a "
        "soft error",
        reinterpret_cast<char *>(&svc.retry_interval) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(
        prefix + "notification_interval",
        "Interval of periodic notification or 0 if its off",
        reinterpret_cast<char *>(&svc.notification_interval) - ref,
        indirect_offset));
    table->addColumn(new OffsetDoubleColumn(
        prefix + "first_notification_delay",
        "Delay before the first notification",
        reinterpret_cast<char *>(&svc.first_notification_delay) - ref,
        indirect_offset));
    table->addColumn(new OffsetDoubleColumn(
        prefix + "low_flap_threshold", "Low threshold of flap detection",
        reinterpret_cast<char *>(&svc.low_flap_threshold) - ref,
        indirect_offset));
    table->addColumn(new OffsetDoubleColumn(
        prefix + "high_flap_threshold", "High threshold of flap detection",
        reinterpret_cast<char *>(&svc.high_flap_threshold) - ref,
        indirect_offset));
    table->addColumn(new OffsetDoubleColumn(
        prefix + "latency",
        "Time difference between scheduled check time and actual check time",
        reinterpret_cast<char *>(&svc.latency) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(
        prefix + "execution_time",
        "Time the service check needed for execution",
        reinterpret_cast<char *>(&svc.execution_time) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(
        prefix + "percent_state_change", "Percent state change",
        reinterpret_cast<char *>(&svc.percent_state_change) - ref,
        indirect_offset));

    table->addColumn(new OffsetTimeperiodColumn(
        prefix + "in_check_period",
        "Whether the service is currently in its check period (0/1)",
        reinterpret_cast<char *>(&svc.check_period_ptr) - ref,
        indirect_offset));
    table->addColumn(new CustomTimeperiodColumn(
        prefix + "in_service_period",
        "Whether this service is currently in its service period (0/1)",
        reinterpret_cast<char *>(&svc.custom_variables) - ref, indirect_offset,
        "SERVICE_PERIOD"));
    table->addColumn(new OffsetTimeperiodColumn(
        prefix + "in_notification_period",
        "Whether the service is currently in its notification period (0/1)",
        reinterpret_cast<char *>(&svc.notification_period_ptr) - ref,
        indirect_offset));

    table->addColumn(new ServiceContactsColumn(prefix + "contacts",
                                               "A list of all contacts of the "
                                               "service, either direct or via "
                                               "a contact group",
                                               indirect_offset));
    table->addColumn(new DownCommColumn(
        prefix + "downtimes", "A list of all downtime ids of the service",
        indirect_offset, downtimes_holder, true, true, false, false));
    table->addColumn(new DownCommColumn(
        prefix + "downtimes_with_info",
        "A list of all downtimes of the service with id, author and comment",
        indirect_offset, downtimes_holder, true, true, true, false));
    table->addColumn(new DownCommColumn(
        prefix + "comments", "A list of all comment ids of the service",
        indirect_offset, comments_holder, false, true, false, false));
    table->addColumn(new DownCommColumn(
        prefix + "comments_with_info",
        "A list of all comments of the service with id, author and comment",
        indirect_offset, comments_holder, false, true, true, false));
    table->addColumn(new DownCommColumn(
        prefix + "comments_with_extra_info",
        "A list of all comments of the service with id, author, comment, entry "
        "type and entry time",
        indirect_offset, comments_holder, false, true, true, true));

    if (add_hosts) {
        TableHosts::addColumns(table, "host_",
                               reinterpret_cast<char *>(&svc.host_ptr) - ref,
                               -1, downtimes_holder, comments_holder, core);
    }

    table->addColumn(new CustomVarsNamesColumn(
        prefix + "custom_variable_names",
        "A list of the names of all custom variables of the service",
        reinterpret_cast<char *>(&svc.custom_variables) - ref,
        indirect_offset));
    table->addColumn(new CustomVarsValuesColumn(
        prefix + "custom_variable_values",
        "A list of the values of all custom variable of the service",
        reinterpret_cast<char *>(&svc.custom_variables) - ref,
        indirect_offset));
    table->addColumn(new CustomVarsDictColumn(
        prefix + "custom_variables", "A dictionary of the custom variables",
        reinterpret_cast<char *>(&svc.custom_variables) - ref,
        indirect_offset));

    table->addColumn(new ServiceGroupsColumn(
        prefix + "groups", "A list of all service groups the service is in",
        reinterpret_cast<char *>(&svc.servicegroups_ptr) - ref,
        indirect_offset));
    table->addColumn(new ContactGroupsColumn(
        prefix + "contact_groups",
        "A list of all contact groups this service is in",
        reinterpret_cast<char *>(&svc.contact_groups) - ref, indirect_offset,
        -1, core));

    table->addColumn(new MetricsColumn(
        prefix + "metrics",
        "A dummy column in order to be compatible with Check_MK Multisite",
        indirect_offset, -1));
    table->addColumn(new FixedIntColumn(
        prefix + "cached_at",
        "A dummy column in order to be compatible with Check_MK Multisite", 0));
    table->addColumn(new FixedIntColumn(
        prefix + "cache_interval",
        "A dummy column in order to be compatible with Check_MK Multisite", 0));
}

void TableServices::answerQuery(Query *query) {
    // do we know the host?
    if (const string *value = query->findValueForIndexing("host_name")) {
        // Older Nagios headers are not const-correct... :-P
        if (host *host = find_host(const_cast<char *>(value->c_str()))) {
            for (servicesmember *m = host->services; m != nullptr;
                 m = m->next) {
                if (!query->processDataset(m->service_ptr)) {
                    break;
                }
            }
            return;
        }
    }

    // do we know the service group?
    if (const string *name = query->findValueForIndexing("groups")) {
        if (servicegroup *sg =
                find_servicegroup(const_cast<char *>(name->c_str()))) {
            for (servicesmember *m = sg->members; m != nullptr; m = m->next) {
                if (!query->processDataset(m->service_ptr)) {
                    break;
                }
            }
        }
        return;
    }

    // do we know the host group?
    if (const string *name = query->findValueForIndexing("host_groups")) {
        if (hostgroup *hg = find_hostgroup(const_cast<char *>(name->c_str()))) {
            for (hostsmember *m = hg->members; m != nullptr; m = m->next) {
                for (servicesmember *smem = m->host_ptr->services;
                     smem != nullptr; smem = smem->next) {
                    if (!query->processDataset(smem->service_ptr)) {
                        break;
                    }
                }
            }
        }
        return;
    }

    // no index -> iterator over *all* services
    for (service *svc = service_list; svc != nullptr; svc = svc->next) {
        if (!query->processDataset(svc)) {
            break;
        }
    }
}

bool TableServices::isAuthorized(contact *ctc, void *data) {
    service *svc = static_cast<service *>(data);
    return is_authorized_for(ctc, svc->host_ptr, svc);
}

void *TableServices::findObject(const string &objectspec) {
    return getServiceBySpec(objectspec);
}
