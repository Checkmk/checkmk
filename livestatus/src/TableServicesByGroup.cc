// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableServicesByGroup.h"

#include "Column.h"
#include "MonitoringCore.h"
#include "NagiosGlobals.h"
#include "Query.h"
#include "Row.h"
#include "TableServiceGroups.h"
#include "TableServices.h"
#include "auth.h"
#include "nagios.h"

namespace {
struct servicebygroup {
    const service *svc;
    const servicegroup *service_group;
};
}  // namespace

TableServicesByGroup::TableServicesByGroup(MonitoringCore *mc) : Table(mc) {
    ColumnOffsets offsets{};
    TableServices::addColumns(this, "", offsets.add([](Row r) {
        return r.rawData<servicebygroup>()->svc;
    }),
                              true);
    TableServiceGroups::addColumns(
        this, "servicegroup_", offsets.add([](Row r) {
            return r.rawData<servicebygroup>()->service_group;
        }));
}

std::string TableServicesByGroup::name() const { return "servicesbygroup"; }

std::string TableServicesByGroup::namePrefix() const { return "service_"; }

void TableServicesByGroup::answerQuery(Query *query) {
    for (const servicegroup *sg = servicegroup_list; sg != nullptr;
         sg = sg->next) {
        if (is_authorized_for_service_group(core()->groupAuthorization(),
                                            core()->serviceAuthorization(), sg,
                                            query->authUser())) {
            for (const servicesmember *m = sg->members; m != nullptr;
                 m = m->next) {
                servicebygroup sbg{m->service_ptr, sg};
                if (!query->processDataset(Row(&sbg))) {
                    return;
                }
            }
        }
    }
}

bool TableServicesByGroup::isAuthorized(Row row, const contact *ctc) const {
    const auto *svc = rowData<servicebygroup>(row)->svc;
    return is_authorized_for(core()->serviceAuthorization(), ctc, svc->host_ptr,
                             svc);
}
