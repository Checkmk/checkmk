// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableServicesByHostGroup.h"

#include "TableHostGroups.h"
#include "TableServices.h"
#include "livestatus/Column.h"
#include "livestatus/Interface.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/User.h"

namespace {
struct ServiceAndGroup {
    const IService &svc;
    const IHostGroup &group;
};
}  // namespace

TableServicesByHostGroup::TableServicesByHostGroup(MonitoringCore *mc)
    : Table(mc) {
    const ColumnOffsets offsets{};
    TableServices::addColumns(this, "", offsets.add([](Row r) {
        return r.rawData<ServiceAndGroup>()->svc.handle();
    }),
                              TableServices::AddHosts::yes, LockComments::yes,
                              LockDowntimes::yes);
    TableHostGroups::addColumns(this, "hostgroup_", offsets.add([](Row r) {
        return r.rawData<ServiceAndGroup>()->group.handle();
    }));
}

std::string TableServicesByHostGroup::name() const {
    return "servicesbyhostgroup";
}

std::string TableServicesByHostGroup::namePrefix() const { return "service_"; }

void TableServicesByHostGroup::answerQuery(Query &query, const User &user) {
    core()->all_of_host_groups([&user, &query](const IHostGroup &hg) {
        return hg.all([&hg, &user, &query](const IHost &host) {
            return host.all_of_services(
                [&hg, &user, &query](const IService &svc) {
                    ServiceAndGroup sag = {.svc{svc}, .group{hg}};
                    return !user.is_authorized_for_service(svc) ||
                           query.processDataset(Row{&sag});
                });
        });
    });
}
