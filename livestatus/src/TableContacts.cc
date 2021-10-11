// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableContacts.h"

// We need it for std::transform, but IWYU "oscillates" a bit here... :-/
#include <algorithm>  // IWYU pragma: keep
#include <iterator>
#include <memory>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "AttributeBitmaskColumn.h"
#include "AttributeListColumn.h"
#include "AttributesLambdaColumn.h"
#include "BoolColumn.h"
#include "Column.h"
#include "IntColumn.h"
#include "ListLambdaColumn.h"
#include "MonitoringCore.h"
#include "NagiosGlobals.h"
#include "Query.h"
#include "StringColumn.h"
#include "TimeperiodsCache.h"
#include "nagios.h"

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
extern TimeperiodsCache *g_timeperiods_cache;

using namespace std::literals;

namespace {
template <typename T>
std::vector<typename T::key_type> map_keys(const T &map) {
    std::vector<typename T::key_type> out;
    out.reserve(map.size());
    std::transform(
        std::begin(map), std::end(map), std::back_inserter(out),
        [](const typename T::value_type &pair) { return pair.first; });
    return out;
}

template <typename T>
std::vector<typename T::mapped_type> map_values(const T &map) {
    std::vector<typename T::mapped_type> out;
    out.reserve(map.size());
    std::transform(
        std::begin(map), std::end(map), std::back_inserter(out),
        [](const typename T::value_type &pair) { return pair.second; });
    return out;
}

class CustomAttributeMap {
public:
    class Keys;
    class Values;
    CustomAttributeMap(const MonitoringCore *const mc, const AttributeKind kind)
        : mc_{mc}, kind_{kind} {}
    Attributes operator()(const contact &ct) {
        if (const auto *p = ct.custom_variables) {
            return mc_->customAttributes(&p, kind_);
        }
        return {};
    };

private:
    const MonitoringCore *const mc_;
    const AttributeKind kind_;
};

class CustomAttributeMap::Keys {
public:
    Keys(const MonitoringCore *const mc, const AttributeKind kind)
        : m_{mc, kind} {}
    std::vector<Attributes::key_type> operator()(const contact &ct) {
        return map_keys(m_(ct));
    }

private:
    CustomAttributeMap m_;
};

class CustomAttributeMap::Values {
public:
    Values(const MonitoringCore *const mc, const AttributeKind kind)
        : m_{mc, kind} {}
    std::vector<Attributes::mapped_type> operator()(const contact &ct) {
        return map_values(m_(ct));
    }

private:
    CustomAttributeMap m_;
};

}  // namespace

TableContacts::TableContacts(MonitoringCore *mc) : Table(mc) {
    addColumns(this, "", ColumnOffsets{});
}

std::string TableContacts::name() const { return "contacts"; }

std::string TableContacts::namePrefix() const { return "contact_"; }

// static
void TableContacts::addColumns(Table *table, const std::string &prefix,
                               const ColumnOffsets &offsets) {
    auto *mc = table->core();
    table->addColumn(std::make_unique<StringColumn::Callback<contact>>(
        prefix + "name", "The login name of the contact person", offsets,
        [](const contact &ct) { return ct.name == nullptr ? ""s : ct.name; }));
    table->addColumn(std::make_unique<StringColumn::Callback<contact>>(
        prefix + "alias", "The full name of the contact", offsets,
        [](const contact &ct) {
            return ct.alias == nullptr ? ""s : ct.alias;
        }));
    table->addColumn(std::make_unique<StringColumn::Callback<contact>>(
        prefix + "email", "The email address of the contact", offsets,
        [](const contact &ct) {
            return ct.email == nullptr ? ""s : ct.email;
        }));
    table->addColumn(std::make_unique<StringColumn::Callback<contact>>(
        prefix + "pager", "The pager address of the contact", offsets,
        [](const contact &ct) {
            return ct.pager == nullptr ? ""s : ct.pager;
        }));
    table->addColumn(std::make_unique<StringColumn::Callback<contact>>(
        prefix + "host_notification_period",
        "The time period in which the contact will be notified about host problems",
        offsets, [](const contact &ct) {
            return ct.host_notification_period == nullptr
                       ? ""s
                       : ct.host_notification_period;
        }));
    table->addColumn(std::make_unique<StringColumn::Callback<contact>>(
        prefix + "service_notification_period",
        "The time period in which the contact will be notified about service problems",
        offsets, [](const contact &ct) {
            return ct.service_notification_period == nullptr
                       ? ""s
                       : ct.service_notification_period;
        }));
    for (int i = 0; i < MAX_CONTACT_ADDRESSES; ++i) {
        std::string b = "address" + std::to_string(i + 1);
        table->addColumn(std::make_unique<StringColumn::Callback<contact>>(
            prefix + b, "The additional field " + b, offsets,
            [i](const contact &ct) {
                return ct.address[i] == nullptr ? ""s : ct.address[i];
            }));
    }

    table->addColumn(std::make_unique<IntColumn::Callback<contact>>(
        prefix + "can_submit_commands",
        "Wether the contact is allowed to submit commands (0/1)", offsets,
        [](const contact &ct) { return ct.can_submit_commands; }));
    table->addColumn(std::make_unique<IntColumn::Callback<contact>>(
        prefix + "host_notifications_enabled",
        "Wether the contact will be notified about host problems in general (0/1)",
        offsets,
        [](const contact &ct) { return ct.host_notifications_enabled; }));
    table->addColumn(std::make_unique<IntColumn::Callback<contact>>(
        prefix + "service_notifications_enabled",
        "Wether the contact will be notified about service problems in general (0/1)",
        offsets,
        [](const contact &ct) { return ct.service_notifications_enabled; }));
    table->addColumn(std::make_unique<BoolColumn::Callback<contact>>(
        prefix + "in_host_notification_period",
        "Wether the contact is currently in his/her host notification period (0/1)",
        offsets, [](const contact &ct) {
            return g_timeperiods_cache->inTimeperiod(
                ct.host_notification_period_ptr);
        }));
    table->addColumn(std::make_unique<BoolColumn::Callback<contact>>(
        prefix + "in_service_notification_period",
        "Wether the contact is currently in his/her service notification period (0/1)",
        offsets, [](const contact &ct) {
            return g_timeperiods_cache->inTimeperiod(
                ct.service_notification_period_ptr);
        }));
    table->addColumn(std::make_unique<ListColumn::Callback<contact>>(
        prefix + "custom_variable_names",
        "A list of all custom variables of the contact", offsets,
        CustomAttributeMap::Keys{mc, AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<ListColumn::Callback<contact>>(
        prefix + "custom_variable_values",
        "A list of the values of all custom variables of the contact", offsets,
        CustomAttributeMap::Values{mc, AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<contact>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets,
        CustomAttributeMap{table->core(), AttributeKind::custom_variables}));

    table->addColumn(std::make_unique<ListColumn::Callback<contact>>(
        prefix + "tag_names", "A list of all tags of the contact", offsets,
        CustomAttributeMap::Keys{mc, AttributeKind::tags}));
    table->addColumn(std::make_unique<ListColumn::Callback<contact>>(
        prefix + "tag_values",
        "A list of the values of all tags of the contact", offsets,
        CustomAttributeMap::Values{mc, AttributeKind::tags}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<contact>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        CustomAttributeMap{table->core(), AttributeKind::tags}));

    table->addColumn(std::make_unique<ListColumn::Callback<contact>>(
        prefix + "label_names", "A list of all labels of the contact", offsets,
        CustomAttributeMap::Keys{mc, AttributeKind::labels}));
    table->addColumn(std::make_unique<ListColumn::Callback<contact>>(
        prefix + "label_values",
        "A list of the values of all labels of the contact", offsets,
        CustomAttributeMap::Values{mc, AttributeKind::labels}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<contact>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        CustomAttributeMap{table->core(), AttributeKind::labels}));

    table->addColumn(std::make_unique<ListColumn::Callback<contact>>(
        prefix + "label_source_names", "A list of all sources of the contact",
        offsets, CustomAttributeMap::Keys{mc, AttributeKind::label_sources}));
    table->addColumn(std::make_unique<ListColumn::Callback<contact>>(
        prefix + "label_source_values",
        "A list of the values of all sources of the contact", offsets,
        CustomAttributeMap::Values{mc, AttributeKind::label_sources}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<contact>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        CustomAttributeMap{table->core(), AttributeKind::label_sources}));

    table->addColumn(std::make_unique<AttributeBitmaskColumn<contact>>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified", offsets,
        [](const contact &ct) { return ct.modified_attributes; }));
    table->addColumn(std::make_unique<AttributeListColumn<contact>>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", offsets,
        [](const contact &ct) { return ct.modified_attributes; }));
}

void TableContacts::answerQuery(Query *query) {
    for (const contact *ct = contact_list; ct != nullptr; ct = ct->next) {
        if (!query->processDataset(Row{ct})) {
            break;
        }
    }
}

Row TableContacts::get(const std::string &primary_key) const {
    // "name" is the primary key
    return Row(core()->find_contact(primary_key));
}
