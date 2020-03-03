// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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
