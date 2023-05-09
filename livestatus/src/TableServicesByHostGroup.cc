// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableServicesByHostGroup.h"

#include "Column.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "Row.h"
#include "TableHostGroups.h"
#include "TableServices.h"
#include "auth.h"
#include "nagios.h"

namespace {
struct service_and_group {
    const service *svc;
    const hostgroup *group;
};
}  // namespace

TableServicesByHostGroup::TableServicesByHostGroup(MonitoringCore *mc)
    : Table(mc) {
    ColumnOffsets offsets{};
    TableServices::addColumns(this, "", offsets.add([](Row r) {
        return r.rawData<service_and_group>()->svc;
    }),
                              true);
    TableHostGroups::addColumns(this, "hostgroup_", offsets.add([](Row r) {
        return r.rawData<service_and_group>()->group;
    }));
}

std::string TableServicesByHostGroup::name() const {
    return "servicesbyhostgroup";
}

std::string TableServicesByHostGroup::namePrefix() const { return "service_"; }

void TableServicesByHostGroup::answerQuery(Query *query) {
    auto process = [query, service_auth = core()->serviceAuthorization(),
                    auth_user = query->authUser()](const service *svc,
                                                   const hostgroup *group) {
        service_and_group sag{svc, group};
        return !is_authorized_for_svc(service_auth, auth_user, svc) ||
               query->processDataset(Row{&sag});
    };

    for (const auto *group = hostgroup_list; group != nullptr;
         group = group->next) {
        for (const auto *hm = group->members; hm != nullptr; hm = hm->next) {
            for (const auto *sm = hm->host_ptr->services; sm != nullptr;
                 sm = sm->next) {
                if (!process(sm->service_ptr, group)) {
                    return;
                }
            }
        }
    }
}
