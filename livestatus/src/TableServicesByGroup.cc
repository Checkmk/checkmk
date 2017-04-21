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
#include "Query.h"
#include "TableServiceGroups.h"
#include "TableServices.h"
#include "WorldNagios.h"
#include "auth.h"
#include "nagios.h"

using std::string;

extern servicegroup *servicegroup_list;

namespace {
struct servicebygroup {
    service _service;
    servicegroup *_servicegroup;
};
}  // namespace

TableServicesByGroup::TableServicesByGroup(MonitoringCore *mc) : Table(mc) {
    TableServices::addColumns(this, mc, "", -1, true);
    TableServiceGroups::addColumns(
        this, "servicegroup_",
        DANGEROUS_OFFSETOF(servicebygroup, _servicegroup));
}

string TableServicesByGroup::name() const { return "servicesbygroup"; }

string TableServicesByGroup::namePrefix() const { return "service_"; }

void TableServicesByGroup::answerQuery(Query *query) {
    // When g_group_authorization is set to AuthorizationKind::strict we need to
    // pre-check if every service of this group is visible to the _auth_user
    bool requires_precheck = (query->authUser() != nullptr) &&
                             g_group_authorization == AuthorizationKind::strict;

    for (servicegroup *sg = servicegroup_list; sg != nullptr; sg = sg->next) {
        bool show_service_group = true;
        if (requires_precheck) {
            for (servicesmember *m = sg->members; m != nullptr; m = m->next) {
                if (!is_authorized_for(query->authUser(),
                                       m->service_ptr->host_ptr,
                                       m->service_ptr)) {
                    show_service_group = false;
                    break;
                }
            }
        }

        if (show_service_group) {
            for (servicesmember *m = sg->members; m != nullptr; m = m->next) {
                servicebygroup sbg = {*m->service_ptr, sg};
                if (!query->processDataset(Row(&sbg))) {
                    break;
                }
            }
        }
    }
}

bool TableServicesByGroup::isAuthorized(Row row, contact *ctc) {
    service *svc = rowData<service>(row);
    return is_authorized_for(ctc, svc->host_ptr, svc);
}

Row TableServicesByGroup::findObject(const string &objectspec) {
    return Row(getServiceBySpec(objectspec));
}
