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
    for (const auto *group = servicegroup_list; group != nullptr;
         group = group->next) {
        if (core()->groupAuthorization() == GroupAuthorization::loose ||
            is_authorized_for_service_group(core()->groupAuthorization(),
                                            core()->serviceAuthorization(),
                                            group, query->authUser())) {
            for (const auto *m = group->members; m != nullptr; m = m->next) {
                service_and_group sag{m->service_ptr, group};
                if (!query->processDataset(Row(&sag))) {
                    return;
                }
            }
        }
    }
}

bool TableServicesByGroup::isAuthorized(Row row, const contact *ctc) const {
    return is_authorized_for_svc(core()->serviceAuthorization(), ctc,
                                 rowData<service_and_group>(row)->svc);
}
