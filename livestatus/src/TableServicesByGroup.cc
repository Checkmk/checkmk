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

#include "TableServicesByGroup.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "TableServiceGroups.h"
#include "TableServices.h"
#include "auth.h"
#include "nagios.h"

extern servicegroup *servicegroup_list;

namespace {
struct servicebygroup {
    service svc;
    // cppcheck is too dumb to see usage in the DANGEROUS_OFFSETOF macro
    // cppcheck-suppress unusedStructMember
    servicegroup *service_group;
};
}  // namespace

TableServicesByGroup::TableServicesByGroup(MonitoringCore *mc) : Table(mc) {
    TableServices::addColumns(this, "", -1, true);
    TableServiceGroups::addColumns(
        this, "servicegroup_",
        DANGEROUS_OFFSETOF(servicebygroup, service_group));
}

std::string TableServicesByGroup::name() const { return "servicesbygroup"; }

std::string TableServicesByGroup::namePrefix() const { return "service_"; }

void TableServicesByGroup::answerQuery(Query *query) {
    bool requires_authcheck =
        query->authUser() != nullptr &&
        core()->groupAuthorization() == AuthorizationKind::strict;

    for (servicegroup *sg = servicegroup_list; sg != nullptr; sg = sg->next) {
        if (requires_authcheck &&
            !is_authorized_for_service_group(core(), sg, query->authUser())) {
            continue;
        }

        for (servicesmember *m = sg->members; m != nullptr; m = m->next) {
            servicebygroup sbg = {*m->service_ptr, sg};
            if (!query->processDataset(Row(&sbg))) {
                return;
            }
        }
    }
}

bool TableServicesByGroup::isAuthorized(Row row, const contact *ctc) const {
    auto svc = &rowData<servicebygroup>(row)->svc;
    return is_authorized_for(core(), ctc, svc->host_ptr, svc);
}
