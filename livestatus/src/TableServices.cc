// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "nagios.h"
#include "TableServices.h"
#include "Query.h"
#include "logger.h"
#include "OffsetStringColumn.h"
#include "OffsetIntColumn.h"
#include "OffsetTimeColumn.h"
#include "OffsetDoubleColumn.h"
#include "OffsetTimeperiodColumn.h"
#include "OffsetStringServiceMacroColumn.h"
#include "ServiceSpecialIntColumn.h"
#include "ServiceSpecialDoubleColumn.h"
#include "AttributelistColumn.h"
#include "TableHosts.h"
#include "TableServicegroups.h"
#include "TableHostgroups.h"
#include "ServiceContactsColumn.h"
#include "DownCommColumn.h"
#include "CustomVarsColumn.h"
#include "ServicegroupsColumn.h"
#include "ContactgroupsColumn.h"
#include "tables.h"
#include "auth.h"
#include "strutil.h"

extern service *service_list;
extern servicegroup *servicegroup_list;
extern hostgroup *hostgroup_list;

struct servicebygroup {
    service _service;
    servicegroup *_servicegroup;
};
struct servicebyhostgroup {
    service _service;
    hostgroup *_hostgroup;
};

void TableServices::answerQuery(Query *query)
{
    // Table servicesbygroup iterate over service groups
    if (_by_group) {
        servicegroup *sgroup = servicegroup_list;
        servicebygroup sg;
        while (sgroup) {
            sg._servicegroup = sgroup;
            servicesmember *mem = sgroup->members;
            while (mem) {
                memcpy(&sg._service, mem->service_ptr, sizeof(service));
                if (!query->processDataset(&sg))
                    break;
                mem = mem->next;
            }
            sgroup = sgroup->next;
        }
        return;
    }

    // Table servicesbyhostgroup iterates of hostgroups and hosts
    else if (_by_hostgroup)
    {
        hostgroup *hgroup = hostgroup_list;
        servicebyhostgroup shg;
        while (hgroup) {
            shg._hostgroup = hgroup;
            hostsmember *mem = hgroup->members;
            while (mem) {
                host *hst = mem->host_ptr;
                servicesmember *smem = hst->services;
                while (smem) {
                    service *svc = smem->service_ptr;
                    memcpy(&shg._service, svc, sizeof(service));
                    if (!query->processDataset(&shg))
                        break;
                    smem = smem->next;
                }
                mem = mem->next;
            }
            hgroup = hgroup->next;
        }
        return;
    }


    // do we know the host?
    char *host_name = (char *)query->findIndexFilter("host_name");
    if (host_name) {
        host *host = find_host(host_name);
        if (host) {
            servicesmember *mem = host->services;
            while (mem) {
                if (!query->processDataset(mem->service_ptr))
                    break;
                mem = mem->next;
            }
        }
        return;
    }

    // do we know the service group?
    servicegroup *sgroup = (servicegroup *)query->findIndexFilter("groups");
    if (sgroup) {
        servicesmember *mem = sgroup->members;
        while (mem) {
            if (!query->processDataset(mem->service_ptr))
                break;
            mem = mem->next;
        }
        return;
    }

    // do we know the host group?
    hostgroup *hgroup = (hostgroup *)query->findIndexFilter("host_groups");
    if (hgroup) {
        hostsmember *mem = hgroup->members;
        while (mem) {
            host *host = mem->host_ptr;
            servicesmember *smem = host->services;
            while (smem) {
                if (!query->processDataset(smem->service_ptr))
                    break;
                smem = smem->next;
            }
            mem = mem->next;
        }
        return;
    }

    // no index -> iterator over *all* services
    service *svc = service_list;
    while (svc) {
        if (!query->processDataset(svc))
            break;
        svc = svc->next;
    }
}

bool TableServices::isAuthorized(contact *ctc, void *data)
{
    service *svc = (service *)data;
    return is_authorized_for(ctc, svc->host_ptr, svc);
}


TableServices::TableServices(bool by_group, bool by_hostgroup)
  : _by_group(by_group)
  , _by_hostgroup(by_hostgroup)
{
    struct servicebygroup     sgref;
    struct servicebyhostgroup hgref;
    addColumns(this, "", -1, true);
    if (by_group) {
        g_table_servicegroups->addColumns(this, "servicegroup_", (char *)&(sgref._servicegroup) - (char *)&sgref);
    }
    else if (by_hostgroup) {
        g_table_hostgroups->addColumns(this, "hostgroup_", (char *)&(hgref._hostgroup) - (char *)&hgref);
    }
}


void TableServices::addColumns(Table *table, string prefix, int indirect_offset, bool add_hosts)
{
    /* es fehlt noch: double-Spalten, unsigned long spalten, etliche weniger wichtige
       Spalte. Und: die Servicegruppen */

    service svc;
    const char *ref = (const char *)&svc;
    table->addColumn(new OffsetStringColumn(prefix + "description",
                "Description of the service (also used as key)", (char *)(&svc.description) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "display_name",
                "An optional display name (not used by Nagios standard web pages)", (char *)(&svc.display_name) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "check_command",
                "Nagios command used for active checks", (char *)(&svc.service_check_command) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(prefix + "check_command_expanded",
                "Nagios command used for active checks with the macros expanded", (char *)(&svc.service_check_command) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "event_handler",
                "Nagios command used as event handler", (char *)(&svc.event_handler) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "plugin_output",
                "Output of the last check plugin", (char *)(&svc.plugin_output) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "long_plugin_output",
                "Unabbreviated output of the last check plugin", (char *)(&svc.long_plugin_output) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "perf_data",
                "Performance data of the last check plugin", (char *)(&svc.perf_data) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "notification_period",
                "The name of the notification period of the service. It this is empty, service problems are always notified.", (char *)(&svc.notification_period) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "check_period",
                "The name of the check period of the service. It this is empty, the service is always checked.", (char *)(&svc.check_period) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "notes",
                "Optional notes about the service", (char *)(&svc.notes) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(prefix + "notes_expanded",
                "The notes with (the most important) macros expanded", (char *)(&svc.notes) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "notes_url",
                "An optional URL for additional notes about the service", (char *)(&svc.notes_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(prefix + "notes_url_expanded",
                "The notes_url with (the most important) macros expanded", (char *)(&svc.notes_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "action_url",
                "An optional URL for actions or custom information about the service", (char *)(&svc.action_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(prefix + "action_url_expanded",
                "The action_url with (the most important) macros expanded", (char *)(&svc.action_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "icon_image",
                "The name of an image to be used as icon in the web interface", (char *)(&svc.icon_image) - ref, indirect_offset));
    table->addColumn(new OffsetStringServiceMacroColumn(prefix + "icon_image_expanded",
                "The icon_image with (the most important) macros expanded", (char *)(&svc.icon_image) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "icon_image_alt",
                "An alternative text for the icon_image for browsers not displaying icons", (char *)(&svc.icon_image_alt) - ref, indirect_offset));

    table->addColumn(new OffsetIntColumn(prefix + "initial_state",
                "The initial state of the service", (char *)&svc.initial_state - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "max_check_attempts",
                "The maximum number of check attempts", (char *)&svc.max_attempts - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "current_attempt",
                "The number of the current check attempt", (char *)&svc.current_attempt - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "state",
                "The current state of the service (0: OK, 1: WARN, 2: CRITICAL, 3: UNKNOWN)", (char *)&svc.current_state - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "has_been_checked",
                "Whether the service already has been checked (0/1)", (char *)&svc.has_been_checked - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "last_state",
                "The last state of the service", (char *)&svc.last_state - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "last_hard_state",
                "The last hard state of the service", (char *)&svc.last_hard_state - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "state_type",
                "The type of the current state (0: soft, 1: hard)", (char *)&svc.state_type - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "check_type",
                "The type of the last check (0: active, 1: passive)", (char *)&svc.check_type - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "acknowledged",
                "Whether the current service problem has been acknowledged (0/1)", (char *)&svc.problem_has_been_acknowledged - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "acknowledgement_type",
                "The type of the acknownledgement (0: none, 1: normal, 2: sticky)", (char *)&svc.acknowledgement_type - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "no_more_notifications",
                "Whether to stop sending notifications (0/1)", (char *)(&svc.no_more_notifications) - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "last_state_change",
                "The time of the last state change (Unix timestamp)", (char *)&svc.last_state_change - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "last_time_ok",
                "The last time the service was OK (Unix timestamp)", (char *)&svc.last_time_ok - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "last_time_warning",
                "The last time the service was in WARNING state (Unix timestamp)", (char *)&svc.last_time_warning - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "last_time_critical",
                "The last time the service was CRITICAL (Unix timestamp)", (char *)&svc.last_time_critical - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "last_time_unknown",
                "The last time the service was UNKNOWN (Unix timestamp)", (char *)&svc.last_time_unknown - ref, indirect_offset));

    table->addColumn(new OffsetTimeColumn(prefix + "last_check",
                "The time of the last check (Unix timestamp)", (char *)&svc.last_check - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "next_check",
                "The scheduled time of the next check (Unix timestamp)", (char *)&svc.next_check - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "last_notification",
                "The time of the last notification (Unix timestamp)", (char *)&svc.last_notification - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "next_notification",
                "The time of the next notification (Unix timestamp)", (char *)&svc.next_notification - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "current_notification_number",
                "The number of the current notification", (char *)&svc.current_notification_number - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "last_state_change",
                "The time of the last state change - soft or hard (Unix timestamp)", (char *)&svc.last_state_change - ref, indirect_offset));
    table->addColumn(new OffsetTimeColumn(prefix + "last_hard_state_change",
                "The time of the last hard state change (Unix timestamp)", (char *)&svc.last_hard_state_change - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "scheduled_downtime_depth",
                "The number of scheduled downtimes the service is currently in", (char *)(&svc.scheduled_downtime_depth) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "is_flapping",
                "Whether the service is flapping (0/1)", (char *)(&svc.is_flapping) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "checks_enabled",
                "Whether active checks are enabled for the service (0/1)", (char *)(&svc.checks_enabled) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "accept_passive_checks",
                "Whether the service accepts passive checks (0/1)", (char *)(&svc.accept_passive_service_checks) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "event_handler_enabled",
                "Whether and event handler is activated for the service (0/1)", (char *)(&svc.event_handler_enabled) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "notifications_enabled",
                "Whether notifications are enabled for the service (0/1)", (char *)(&svc.notifications_enabled) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "process_performance_data",
                "Whether processing of performance data is enabled for the service (0/1)", (char *)(&svc.process_performance_data) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "is_executing",
                "is there a service check currently running... (0/1)", (char *)(&svc.is_executing) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "active_checks_enabled",
                "Whether active checks are enabled for the service (0/1)", (char *)(&svc.checks_enabled) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "check_options",
                "The current check option, forced, normal, freshness... (0/1)", (char *)(&svc.check_options) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "flap_detection_enabled",
                "Whether flap detection is enabled for the service (0/1)", (char *)(&svc.flap_detection_enabled) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "check_freshness",
                "Whether freshness checks are activated (0/1)", (char *)(&svc.check_freshness) - ref, indirect_offset));
    table->addColumn(new OffsetIntColumn(prefix + "obsess_over_service",
                "Whether 'obsess_over_service' is enabled for the service (0/1)", (char *)(&svc.obsess_over_service) - ref, indirect_offset));
    table->addColumn(new AttributelistColumn(prefix + "modified_attributes",
                "A bitmask specifying which attributes have been modified", (char *)(&svc.modified_attributes) - ref, indirect_offset, false));
    table->addColumn(new AttributelistColumn(prefix + "modified_attributes_list",
                "A list of all modified attributes", (char *)(&svc.modified_attributes) - ref, indirect_offset, true));
    table->addColumn(new ServiceSpecialIntColumn(prefix + "pnpgraph_present",
                "Whether there is a PNP4Nagios graph present for this service (0/1)", SSIC_PNP_GRAPH_PRESENT, indirect_offset));
    table->addColumn(new ServiceSpecialDoubleColumn(prefix + "staleness",
                    "The staleness indicator for this service", SSDC_STALENESS, indirect_offset));

    // columns of type double
    table->addColumn(new OffsetDoubleColumn(prefix + "check_interval",
                "Number of basic interval lengths between two scheduled checks of the service", (char *)(&svc.check_interval) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(prefix + "retry_interval",
                "Number of basic interval lengths between checks when retrying after a soft error", (char *)(&svc.retry_interval) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(prefix + "notification_interval",
                "Interval of periodic notification or 0 if its off", (char *)(&svc.notification_interval) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(prefix + "first_notification_delay",
                "Delay before the first notification", (char *)(&svc.first_notification_delay) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(prefix + "low_flap_threshold",
                "Low threshold of flap detection", (char *)(&svc.low_flap_threshold) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(prefix + "high_flap_threshold",
                "High threshold of flap detection", (char *)(&svc.high_flap_threshold) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(prefix + "latency",
                "Time difference between scheduled check time and actual check time", (char *)(&svc.latency) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(prefix + "execution_time",
                "Time the service check needed for execution", (char *)(&svc.execution_time) - ref, indirect_offset));
    table->addColumn(new OffsetDoubleColumn(prefix + "percent_state_change",
                "Percent state change", (char *)(&svc.percent_state_change) - ref, indirect_offset));


    table->addColumn(new OffsetTimeperiodColumn(prefix + "in_check_period",
                "Whether the service is currently in its check period (0/1)", (char *)&svc.check_period_ptr - ref, indirect_offset));
    table->addColumn(new OffsetTimeperiodColumn(prefix + "in_notification_period",
                "Whether the service is currently in its notification period (0/1)", (char *)&svc.notification_period_ptr - ref, indirect_offset));


    table->addColumn(new ServiceContactsColumn(prefix + "contacts",
                "A list of all contacts of the service, either direct or via a contact group", indirect_offset));
    table->addColumn(new DownCommColumn(prefix + "downtimes",
                "A list of all downtime ids of the service", indirect_offset, true, true, false, false));
    table->addColumn(new DownCommColumn(prefix + "downtimes_with_info",
                "A list of all downtimes of the service with id, author and comment", indirect_offset, true, true, true, false));
    table->addColumn(new DownCommColumn(prefix + "comments",
                "A list of all comment ids of the service", indirect_offset, false, true, false, false));
    table->addColumn(new DownCommColumn(prefix + "comments_with_info",
                "A list of all comments of the service with id, author and comment", indirect_offset, false, true, true, false));
    table->addColumn(new DownCommColumn(prefix + "comments_with_extra_info",
                "A list of all comments of the service with id, author, comment, entry type and entry time", indirect_offset, false, true, true, true));

    if (add_hosts)
        g_table_hosts->addColumns(this, "host_", (char *)(&svc.host_ptr) - ref);

    table->addColumn(new CustomVarsColumn(prefix + "custom_variable_names",
                "A list of the names of all custom variables of the service", (char *)(&svc.custom_variables) - ref, indirect_offset, CVT_VARNAMES));
    table->addColumn(new CustomVarsColumn(prefix + "custom_variable_values",
                "A list of the values of all custom variable of the service", (char *)(&svc.custom_variables) - ref, indirect_offset, CVT_VALUES));
    table->addColumn(new CustomVarsColumn(prefix + "custom_variables",
                "A dictionary of the custom variables", (char *)(&svc.custom_variables) - ref, indirect_offset, CVT_DICT));

    table->addColumn(new ServicegroupsColumn(prefix + "groups",
                "A list of all service groups the service is in", (char *)(&svc.servicegroups_ptr) - ref, indirect_offset));
    table->addColumn(new ContactgroupsColumn(prefix + "contact_groups",
                "A list of all contact groups this service is in", (char *)(&svc.contact_groups) - ref, indirect_offset));
}


void *TableServices::findObject(char *objectspec)
{
    char *host_name;
    char *description;

    // The protocol proposes spaces as a separator between
    // the host name and the service description. That introduces
    // the problem that host name containing spaces will not work.
    // For that reason we alternatively allow a semicolon as a separator.
    char *semicolon = strchr(objectspec, ';');
    if (semicolon) {
        *semicolon = 0;
        host_name = rstrip(objectspec);
        description = rstrip(semicolon + 1);
    }
    else {
        host_name = next_field(&objectspec);
        description = objectspec;
    }
    return find_service(host_name, description);
}
