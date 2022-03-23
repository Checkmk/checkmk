// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableServicesByGroup.h"

#include "Column.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "TableServiceGroups.h"
#include "TableServices.h"
#include "auth.h"
#include "nagios.h"

namespace {
struct service_and_group {
    const service *svc;
    const servicegroup *group;
};
}  // namespace

TableServicesByGroup::TableServicesByGroup(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    TableServices::addColumns(this, "", offsets.add([](Row r) {
        return r.rawData<service_and_group>()->svc;
    }),
                              true);
    TableServiceGroups::addColumns(
        this, "servicegroup_", offsets.add([](Row r) {
            return r.rawData<service_and_group>()->group;
        }));
}

std::string TableServicesByGroup::name() const { return "servicesbygroup"; }

std::string TableServicesByGroup::namePrefix() const { return "service_"; }

void TableServicesByGroup::answerQuery(Query *query) {
    auto process = [query, service_auth = core()->serviceAuthorization(),
                    auth_user = query->authUser()](const service *svc,
                                                   const servicegroup *group) {
        service_and_group sag{svc, group};
        return !is_authorized_for_svc(service_auth, auth_user, svc) ||
               query->processDataset(Row(&sag));
    };

    for (const auto *group = servicegroup_list; group != nullptr;
         group = group->next) {
        if (is_authorized_for_service_group(core()->groupAuthorization(),
                                            core()->serviceAuthorization(),
                                            group, query->authUser())) {
            for (const auto *m = group->members; m != nullptr; m = m->next) {
                if (!process(m->service_ptr, group)) {
                    return;
                }
            }
        }
    }
}
