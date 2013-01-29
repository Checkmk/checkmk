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
#include "TableHostgroups.h"
#include "Query.h"
#include "OffsetStringColumn.h"
#include "HostlistColumn.h"
#include "HostlistStateColumn.h"
#include "auth.h"
#include "tables.h"
#include "TableHosts.h"

/* this might be a hack (accessing Nagios' internal structures.
   Hi Ethan: please help me here: how should this be code to be
   portable? */
extern hostgroup *hostgroup_list;

TableHostgroups::TableHostgroups()
{
    addColumns(this, "", -1);
}

void TableHostgroups::addColumns(Table *table, string prefix, int indirect_offset)
{
    hostgroup hgr;
    char *ref = (char *)&hgr;
    table->addColumn(new OffsetStringColumn(prefix + "name",
                "Name of the hostgroup",       (char *)(&hgr.group_name) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "alias",
                "An alias of the hostgroup",      (char *)(&hgr.alias) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "notes",
                "Optional notes to the hostgroup",      (char *)(&hgr.notes) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "notes_url",
                "An optional URL with further information about the hostgroup",  (char *)(&hgr.notes_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(prefix + "action_url",
                "An optional URL to custom actions or information about the hostgroup", (char *)(&hgr.action_url) - ref, indirect_offset));
    table->addColumn(new HostlistColumn(    prefix + "members",
                "A list of all host names that are members of the hostgroup",    (char *)(&hgr.members) - ref, indirect_offset, false));
    table->addColumn(new HostlistColumn(    prefix + "members_with_state",
                "A list of all host names that are members of the hostgroup together with state and has_been_checked",
                (char *)(&hgr.members) - ref, indirect_offset, true));

    table->addColumn(new HostlistStateColumn(prefix + "worst_host_state",
                "The worst state of all of the groups' hosts (UP <= UNREACHABLE <= DOWN)",     HLSC_WORST_HST_STATE, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_hosts",
                "The total number of hosts in the group",            HLSC_NUM_HST, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_hosts_pending",
                "The number of hosts in the group that are pending",    HLSC_NUM_HST_PENDING, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_hosts_up",
                "The number of hosts in the group that are up",         HLSC_NUM_HST_UP, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_hosts_down",
                "The number of hosts in the group that are down",       HLSC_NUM_HST_DOWN, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_hosts_unreach",
                "The number of hosts in the group that are unreachable",    HLSC_NUM_HST_UNREACH, (char *)(&hgr.members) - ref, indirect_offset));

    table->addColumn(new HostlistStateColumn(prefix + "num_services",
                "The total number of services of hosts in this group",         HLSC_NUM_SVC, (char *)(&hgr.members) - ref, indirect_offset));

    // soft states
    table->addColumn(new HostlistStateColumn(prefix + "worst_service_state",
                "The worst state of all services that belong to a host of this group (OK <= WARN <= UNKNOWN <= CRIT)",  HLSC_WORST_SVC_STATE, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_services_pending",
                "The total number of services with the state Pending of hosts in this group", HLSC_NUM_SVC_PENDING, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_services_ok",
                "The total number of services with the state OK of hosts in this group",      HLSC_NUM_SVC_OK, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_services_warn",
                "The total number of services with the state WARN of hosts in this group",    HLSC_NUM_SVC_WARN, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_services_crit",
                "The total number of services with the state CRIT of hosts in this group",    HLSC_NUM_SVC_CRIT, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_services_unknown",
                "The total number of services with the state UNKNOWN of hosts in this group", HLSC_NUM_SVC_UNKNOWN, (char *)(&hgr.members) - ref, indirect_offset));

    // hard state
    table->addColumn(new HostlistStateColumn(prefix + "worst_service_hard_state",
                "The worst state of all services that belong to a host of this group (OK <= WARN <= UNKNOWN <= CRIT)",  HLSC_WORST_SVC_HARD_STATE, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_services_hard_ok",
                "The total number of services with the state OK of hosts in this group",      HLSC_NUM_SVC_HARD_OK, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_services_hard_warn",
                "The total number of services with the state WARN of hosts in this group",    HLSC_NUM_SVC_HARD_WARN, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_services_hard_crit",
                "The total number of services with the state CRIT of hosts in this group",    HLSC_NUM_SVC_HARD_CRIT, (char *)(&hgr.members) - ref, indirect_offset));
    table->addColumn(new HostlistStateColumn(prefix + "num_services_hard_unknown",
                "The total number of services with the state UNKNOWN of hosts in this group", HLSC_NUM_SVC_HARD_UNKNOWN, (char *)(&hgr.members) - ref, indirect_offset));
}

void TableHostgroups::answerQuery(Query *query)
{
    hostgroup *hg = hostgroup_list;
    while (hg) {
        if (!query->processDataset(hg))
            break;
        hg = hg->next;
    }
}


void *TableHostgroups::findObject(char *objectspec)
{
    return find_hostgroup(objectspec);
}

bool TableHostgroups::isAuthorized(contact *ctc, void *data)
{
    if (ctc == UNKNOWN_AUTH_USER)
        return false;

    hostgroup *hg = (hostgroup *)data;
    hostsmember *mem = hg->members;
    while (mem) {
        host *hst = mem->host_ptr;
        bool is = g_table_hosts->isAuthorized(ctc, hst);
        if (is && g_group_authorization == AUTH_LOOSE)
            return true;
        else if (!is && g_group_authorization == AUTH_STRICT)
            return false;
        mem = mem->next;
    }
    return true;
}
