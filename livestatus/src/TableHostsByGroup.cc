// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableHostsByGroup.h"

#include "TableHostGroups.h"
#include "TableHosts.h"
#include "livestatus/Column.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/User.h"

class IHost;
class IHostGroup;

namespace {
struct host_and_group {
    const IHost *hst;
    const IHostGroup *group;
};
}  // namespace

TableHostsByGroup::TableHostsByGroup(MonitoringCore *mc) : Table(mc) {
    const ColumnOffsets offsets{};
    TableHosts::addColumns(this, "", offsets.add([](Row r) {
        return r.rawData<host_and_group>()->hst;
    }),
                           LockComments::yes, LockDowntimes::yes);
    TableHostGroups::addColumns(this, "hostgroup_", offsets.add([](Row r) {
        return r.rawData<host_and_group>()->group;
    }));
}

std::string TableHostsByGroup::name() const { return "hostsbygroup"; }

std::string TableHostsByGroup::namePrefix() const { return "host_"; }

void TableHostsByGroup::answerQuery(Query &query, const User &user) {
    core()->all_of_host_groups([&query, &user](const auto &hg) {
        return !user.is_authorized_for_host_group(hg) ||
               hg.all([&query, &user, &hg](const IHost &h) {
                   if (!user.is_authorized_for_host(h)) {
                       return true;
                   }
                   host_and_group hag{&h, &hg};
                   return query.processDataset(Row{&hag});
               });
    });
}
