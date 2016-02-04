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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableServicegroups.h"
#include "OffsetStringColumn.h"
#include "Query.h"
#include "ServicelistColumn.h"
#include "ServicelistStateColumn.h"
#include "TableServices.h"
#include "auth.h"
#include "tables.h"

using std::string;

/* this might be a hack (accessing Nagios' internal structures.
Ethan: please help me here: how should this be code to be
portable? */
extern servicegroup *servicegroup_list;

TableServicegroups::TableServicegroups() { addColumns(this, "", -1); }

// static
void TableServicegroups::addColumns(Table *table, string prefix,
                                    int indirect_offset) {
    servicegroup sgr;
    char *ref = reinterpret_cast<char *>(&sgr);
    table->addColumn(new OffsetStringColumn(
        prefix + "name", "The name of the service group",
        reinterpret_cast<char *>(&sgr.group_name) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "alias", "An alias of the service group",
        reinterpret_cast<char *>(&sgr.alias) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "notes", "Optional additional notes about the service group",
        reinterpret_cast<char *>(&sgr.notes) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "notes_url",
        "An optional URL to further notes on the service group",
        reinterpret_cast<char *>(&sgr.notes_url) - ref, indirect_offset));
    table->addColumn(new OffsetStringColumn(
        prefix + "action_url",
        "An optional URL to custom notes or actions on the service group",
        reinterpret_cast<char *>(&sgr.action_url) - ref, indirect_offset));
    table->addColumn(new ServicelistColumn(
        prefix + "members",
        "A list of all members of the service group as host/service pairs",
        reinterpret_cast<char *>(&sgr.members) - ref, indirect_offset, true,
        0));
    table->addColumn(new ServicelistColumn(
        prefix + "members_with_state",
        "A list of all members of the service group with state and "
        "has_been_checked",
        reinterpret_cast<char *>(&sgr.members) - ref, indirect_offset, true,
        1));

    table->addColumn(new ServicelistStateColumn(
        prefix + "worst_service_state",
        "The worst soft state of all of the groups services (OK <= WARN <= "
        "UNKNOWN <= CRIT)",
        SLSC_WORST_STATE, reinterpret_cast<char *>(&sgr.members) - ref,
        indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services", "The total number of services in the group",
        SLSC_NUM, reinterpret_cast<char *>(&sgr.members) - ref,
        indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services_ok",
        "The number of services in the group that are OK", SLSC_NUM_OK,
        reinterpret_cast<char *>(&sgr.members) - ref, indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services_warn",
        "The number of services in the group that are WARN", SLSC_NUM_WARN,
        reinterpret_cast<char *>(&sgr.members) - ref, indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services_crit",
        "The number of services in the group that are CRIT", SLSC_NUM_CRIT,
        reinterpret_cast<char *>(&sgr.members) - ref, indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services_unknown",
        "The number of services in the group that are UNKNOWN",
        SLSC_NUM_UNKNOWN, reinterpret_cast<char *>(&sgr.members) - ref,
        indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services_pending",
        "The number of services in the group that are PENDING",
        SLSC_NUM_PENDING, reinterpret_cast<char *>(&sgr.members) - ref,
        indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services_hard_ok",
        "The number of services in the group that are OK", SLSC_NUM_HARD_OK,
        reinterpret_cast<char *>(&sgr.members) - ref, indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services_hard_warn",
        "The number of services in the group that are WARN", SLSC_NUM_HARD_WARN,
        reinterpret_cast<char *>(&sgr.members) - ref, indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services_hard_crit",
        "The number of services in the group that are CRIT", SLSC_NUM_HARD_CRIT,
        reinterpret_cast<char *>(&sgr.members) - ref, indirect_offset));
    table->addColumn(new ServicelistStateColumn(
        prefix + "num_services_hard_unknown",
        "The number of services in the group that are UNKNOWN",
        SLSC_NUM_HARD_UNKNOWN, reinterpret_cast<char *>(&sgr.members) - ref,
        indirect_offset));
}

void TableServicegroups::answerQuery(Query *query) {
    servicegroup *sg = servicegroup_list;
    while (sg != nullptr) {
        if (!query->processDataset(sg)) {
            break;
        }
        sg = sg->next;
    }
}

void *TableServicegroups::findObject(char *objectspec) {
    return find_servicegroup(objectspec);
}

bool TableServicegroups::isAuthorized(contact *ctc, void *data) {
    if (ctc == UNKNOWN_AUTH_USER) {
        return false;
    }

    servicegroup *sg = reinterpret_cast<servicegroup *>(data);
    servicesmember *mem = sg->members;
    while (mem != nullptr) {
        service *svc = mem->service_ptr;
        bool is = g_table_services->isAuthorized(ctc, svc);
        if (is && g_group_authorization == AUTH_LOOSE) {
            return true;
        }
        if (!is && g_group_authorization == AUTH_STRICT) {
            return false;
        }
        mem = mem->next;
    }
    return true;
}
