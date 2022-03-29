// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableServicesByGroup.h"

#include <optional>

#include "Column.h"
#include "Logger.h"
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

void TableServicesByGroup::answerQuery(Query *query, const User &user) {
    auto process = [&](const service_and_group &sag) {
        return !user.is_authorized_for_service(*sag.svc) ||
               query->processDataset(Row{&sag});
    };

    // If we know the service group, we simply iterate over it.
    if (auto value = query->stringValueRestrictionFor("groups")) {
        Debug(logger()) << "using service group index with '" << *value << "'";
        if (const auto *group =
                find_servicegroup(const_cast<char *>(value->c_str()))) {
            if (user.is_authorized_for_service_group(*group)) {
                for (const auto *m = group->members; m != nullptr;
                     m = m->next) {
                    if (!process(service_and_group{m->service_ptr, group})) {
                        return;
                    }
                }
            }
        }
        return;
    }

    // In the general case, we have to process all service groups.
    Debug(logger()) << "using full table scan";
    for (const auto *group = servicegroup_list; group != nullptr;
         group = group->next) {
        if (user.is_authorized_for_service_group(*group)) {
            for (const auto *m = group->members; m != nullptr; m = m->next) {
                if (!process(service_and_group{m->service_ptr, group})) {
                    return;
                }
            }
        }
    }
}
