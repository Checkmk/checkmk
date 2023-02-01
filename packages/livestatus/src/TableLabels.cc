// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/TableLabels.h"

#include <cstddef>
#include <functional>
#include <memory>
#include <unordered_set>

#include "livestatus/Column.h"
#include "livestatus/Interface.h"
#include "livestatus/MonitoringCore.h"
#include "livestatus/Query.h"
#include "livestatus/Row.h"
#include "livestatus/StringColumn.h"
#include "livestatus/User.h"

namespace {
// TODO(sp) Move this to the interface?
struct NameValue {
    const std::string &name;
    const std::string &value;

    bool operator==(const NameValue &other) const {
        return name == other.name && value == other.value;
    }
    bool operator!=(const NameValue &other) const { return !(*this == other); }
};
}  // namespace

// Taken from WG21 P0814R2, an epic story about a triviality...
template <typename T>
inline void hash_combine(std::size_t &seed, const T &val) {
    seed ^= std::hash<T>{}(val) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
}

template <>
struct std::hash<NameValue> {
    // TODO(sp): Nuke those member types with C++20.
    using argument_type = NameValue;
    using result_type = std::size_t;
    result_type operator()(argument_type const &n) const {
        std::size_t seed{0};
        hash_combine(seed, n.name);
        hash_combine(seed, n.value);
        return seed;
    }
};

TableLabels::TableLabels(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{});
}

std::string TableLabels::name() const { return "labels"; }

std::string TableLabels::namePrefix() const { return "label_"; }

// static
void TableLabels::addColumns(Table *table, const std::string &prefix,
                             const ColumnOffsets &offsets) {
    table->addColumn(std::make_unique<StringColumn<NameValue>>(
        prefix + "name", "The name of the label", offsets,
        [](const NameValue &r) { return r.name; }));
    table->addColumn(std::make_unique<StringColumn<NameValue>>(
        prefix + "value", "The value of the label", offsets,
        [](const NameValue &r) { return r.value; }));
}

void TableLabels::answerQuery(Query &query, const User &user) {
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
    std::unordered_set<NameValue> emitted;
    auto processLabel = [&query, &emitted](const std::string &name,
                                           const std::string &value) {
        NameValue r{name, value};
        const auto &[it, insertion_happened] = emitted.insert(r);
        return !insertion_happened || query.processDataset(Row{&r});
    };

    auto processHost = [&processLabel, &user](const IHost &host) {
        return !user.is_authorized_for_host(host) ||
               host.all_labels(processLabel);
    };

    auto processService = [&processLabel, &user](const IService &service) {
        return !user.is_authorized_for_service(service) ||
               service.all_labels(processLabel);
    };

    auto processHostAndServices = [&processHost,
                                   &processService](const IHost &host) {
        return processHost(host) && host.all_services(processService);
    };

    auto processContact = [&processLabel](const IContact &contact) {
        return contact.all_labels(processLabel);
    };

    core()->all_hosts(processHostAndServices) &&
        core()->all_contacts(processContact);
}
