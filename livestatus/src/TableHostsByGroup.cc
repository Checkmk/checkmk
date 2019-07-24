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

#include "TableHostsByGroup.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "TableHostGroups.h"
#include "TableHosts.h"
#include "auth.h"
#include "nagios.h"

extern host *host_list;
extern hostgroup *hostgroup_list;

namespace {
struct hostbygroup {
    host hst;
    // cppcheck is too dumb to see usage in the DANGEROUS_OFFSETOF macro
    // cppcheck-suppress unusedStructMember
    hostgroup *host_group;
};
}  // namespace

TableHostsByGroup::TableHostsByGroup(MonitoringCore *mc) : Table(mc) {
    TableHosts::addColumns(this, "", -1, -1);
    TableHostGroups::addColumns(this, "hostgroup_",
                                DANGEROUS_OFFSETOF(hostbygroup, host_group));
}

std::string TableHostsByGroup::name() const { return "hostsbygroup"; }

std::string TableHostsByGroup::namePrefix() const { return "host_"; }

void TableHostsByGroup::answerQuery(Query *query) {
    bool requires_authcheck =
        query->authUser() != nullptr &&
        core()->groupAuthorization() == AuthorizationKind::strict;

    for (hostgroup *hg = hostgroup_list; hg != nullptr; hg = hg->next) {
        if (requires_authcheck &&
            !is_authorized_for_host_group(core(), hg, query->authUser())) {
            continue;
        }

        for (hostsmember *m = hg->members; m != nullptr; m = m->next) {
            hostbygroup hbg = {*m->host_ptr, hg};
            if (!query->processDataset(Row(&hbg))) {
                return;
            }
        }
    }
}

bool TableHostsByGroup::isAuthorized(Row row, const contact *ctc) const {
    return is_authorized_for(core(), ctc, &rowData<hostbygroup>(row)->hst,
                             nullptr);
}
