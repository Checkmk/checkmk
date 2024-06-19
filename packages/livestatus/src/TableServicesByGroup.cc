// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableServicesByGroup.h"

#include <functional>
#include <optional>

#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/TableServiceGroups.h"
#include "livestatus/TableServices.h"
#include "livestatus/User.h"

namespace {
struct service_and_group {
    const IService *svc;
    const IServiceGroup *group;
};
}  // namespace

using row_type = service_and_group;

TableServicesByGroup::TableServicesByGroup(ICore *mc) {
    const ColumnOffsets offsets{};
    TableServices::addColumns(
        this, *mc, "",
        offsets.add([](Row r) { return r.rawData<row_type>()->svc; }),
        TableServices::AddHosts::yes, LockComments::yes, LockDowntimes::yes);
    TableServiceGroups::addColumns(
        this, "servicegroup_",
        offsets.add([](Row r) { return r.rawData<row_type>()->group; }));
}

std::string TableServicesByGroup::name() const { return "servicesbygroup"; }

std::string TableServicesByGroup::namePrefix() const { return "service_"; }

namespace {
bool ProcessServiceGroup(Query &query, const User &user,
                         const IServiceGroup &sg) {
    return !user.is_authorized_for_service_group(sg) ||
           sg.all([&query, &user, &sg](const IService &s) {
               if (!user.is_authorized_for_service(s)) {
                   return true;
               }
               row_type row{&s, &sg};
               return query.processDataset(Row{&row});
           });
}
}  // namespace

void TableServicesByGroup::answerQuery(Query &query, const User &user,
                                       const ICore &core) {
    auto *logger = core.loggerLivestatus();
    // If we know the service group, we simply iterate over it.
    if (auto value = query.stringValueRestrictionFor("groups")) {
        Debug(logger) << "using service group index with '" << *value << "'";
        if (const auto *sg = core.find_servicegroup(*value)) {
            ProcessServiceGroup(query, user, *sg);
        }
        return;
    }
    // In the general case, we have to process all service groups.
    Debug(logger) << "using full table scan";
    core.all_of_service_groups([&query, &user](const auto &sg) {
        return ProcessServiceGroup(query, user, sg);
    });
}
