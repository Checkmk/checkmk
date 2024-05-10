// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableLabels.h"

#include <functional>
#include <memory>
#include <unordered_set>

#include "livestatus/Column.h"
#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"
#include "livestatus/User.h"

using row_type = Attribute;

TableLabels::TableLabels() { addColumns(this, "", ColumnOffsets{}); }

std::string TableLabels::name() const { return "labels"; }

std::string TableLabels::namePrefix() const { return "label_"; }

// static
void TableLabels::addColumns(Table *table, const std::string &prefix,
                             const ColumnOffsets &offsets) {
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "name", "The name of the label", offsets,
        [](const row_type &row) { return row.name; }));
    table->addColumn(std::make_unique<StringColumn<row_type>>(
        prefix + "value", "The value of the label", offsets,
        [](const row_type &row) { return row.value; }));
}

void TableLabels::answerQuery(Query &query, const User &user,
                              const ICore &core) {
    // NOTE: Due to the lack of data from real sites, we use a very simple and
    // straightforward algorithm below: We just iterate through all hosts,
    // services, and contacts, filtering out unauthorized entities on the way.
    // To avoid reporting duplicates, we keep track of what we have already
    // produced.
    //
    // If this turns out to be too slow, we could use other approaches, e.g.
    // setting up a big collection upfront, containing pairs with a label and a
    // set of hosts/services/contacts having that label. That way, one can
    // simply iterate over the collection, filtering out unauthorized entities
    // on the way. As already said: It's unclear if that is really an
    // improvement, because there is no data about the number of different
    // labels, hosts, etc. Building such a collection upfront could slow down
    // the startup and need tons of memory. Or perhaps not. ;-)
    std::unordered_set<row_type> emitted;
    auto processLabel = [&query, &emitted](const row_type &row) {
        const auto &[it, insertion_happened] = emitted.insert(row);
        return !insertion_happened || query.processDataset(Row{&row});
    };

    auto processHost = [&processLabel, &user](const IHost &host) {
        return !user.is_authorized_for_host(host) ||
               host.all_of_labels(processLabel);
    };

    auto processService = [&processLabel, &user](const IService &service) {
        return !user.is_authorized_for_service(service) ||
               service.all_of_labels(processLabel);
    };

    auto processHostAndServices = [&processHost,
                                   &processService](const IHost &host) {
        return processHost(host) && host.all_of_services(processService);
    };

    auto processContact = [&processLabel](const IContact &contact) {
        return contact.all_of_labels(processLabel);
    };

    core.all_of_hosts(processHostAndServices) &&
        core.all_of_contacts(processContact);
}
