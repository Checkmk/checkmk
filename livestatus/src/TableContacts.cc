// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableContacts.h"

#include <algorithm>
#include <cstdint>
#include <iosfwd>
#include <iterator>
#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

#include "AttributeListLambdaColumn.h"
#include "AttributesLambdaColumn.h"
#include "BoolLambdaColumn.h"
#include "Column.h"
#include "IntLambdaColumn.h"
#include "ListLambdaColumn.h"
#include "MonitoringCore.h"
#include "Query.h"
#include "StringLambdaColumn.h"
#include "TimeperiodsCache.h"  // IWYU pragma: keep
#include "nagios.h"

extern contact *contact_list;
extern TimeperiodsCache *g_timeperiods_cache;

using namespace std::literals;

namespace {

class GetCustomAttribute {
public:
    GetCustomAttribute(const MonitoringCore *const mc, const AttributeKind kind)
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

template <std::size_t Index>
class GetCustomAttributeElem {
public:
    GetCustomAttributeElem(const MonitoringCore *const mc,
                           const AttributeKind kind)
        : get_attrs_{mc, kind} {}
    std::vector<std::string> operator()(const contact &ct) {
        auto attrs = get_attrs_(ct);
        std::vector<std::string> v(attrs.size());
        std::transform(
            std::cbegin(attrs), std::cend(attrs), std::begin(v),
            [](const auto &entry) { return std::get<Index>(entry); });
        return v;
    }

private:
    GetCustomAttribute get_attrs_;
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
    table->addColumn(std::make_unique<StringLambdaColumn<contact>>(
        prefix + "name", "The login name of the contact person", offsets,
        [](const contact &ct) { return ct.name == nullptr ? ""s : ct.name; }));
    table->addColumn(std::make_unique<StringLambdaColumn<contact>>(
        prefix + "alias", "The full name of the contact", offsets,
        [](const contact &ct) {
            return ct.alias == nullptr ? ""s : ct.alias;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<contact>>(
        prefix + "email", "The email address of the contact", offsets,
        [](const contact &ct) {
            return ct.email == nullptr ? ""s : ct.email;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<contact>>(
        prefix + "pager", "The pager address of the contact", offsets,
        [](const contact &ct) {
            return ct.pager == nullptr ? ""s : ct.pager;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<contact>>(
        prefix + "host_notification_period",
        "The time period in which the contact will be notified about host problems",
        offsets, [](const contact &ct) {
            return ct.host_notification_period == nullptr
                       ? ""s
                       : ct.host_notification_period;
        }));
    table->addColumn(std::make_unique<StringLambdaColumn<contact>>(
        prefix + "service_notification_period",
        "The time period in which the contact will be notified about service problems",
        offsets, [](const contact &ct) {
            return ct.service_notification_period == nullptr
                       ? ""s
                       : ct.service_notification_period;
        }));
    for (int i = 0; i < MAX_CONTACT_ADDRESSES; ++i) {
        std::string b = "address" + std::to_string(i + 1);
        table->addColumn(std::make_unique<StringLambdaColumn<contact>>(
            prefix + b, "The additional field " + b, offsets,
            [i](const contact &ct) {
                return ct.address[i] == nullptr ? ""s : ct.address[i];
            }));
    }

    table->addColumn(std::make_unique<IntLambdaColumn<contact>>(
        prefix + "can_submit_commands",
        "Wether the contact is allowed to submit commands (0/1)", offsets,
        [](const contact &ct) { return ct.can_submit_commands; }));
    table->addColumn(std::make_unique<IntLambdaColumn<contact>>(
        prefix + "host_notifications_enabled",
        "Wether the contact will be notified about host problems in general (0/1)",
        offsets,
        [](const contact &ct) { return ct.host_notifications_enabled; }));
    table->addColumn(std::make_unique<IntLambdaColumn<contact>>(
        prefix + "service_notifications_enabled",
        "Wether the contact will be notified about service problems in general (0/1)",
        offsets,
        [](const contact &ct) { return ct.service_notifications_enabled; }));
    table->addColumn(std::make_unique<BoolLambdaColumn<contact>>(
        prefix + "in_host_notification_period",
        "Wether the contact is currently in his/her host notification period (0/1)",
        offsets, [](const contact &ct) {
            return g_timeperiods_cache->inTimeperiod(
                ct.host_notification_period_ptr);
        }));
    table->addColumn(std::make_unique<BoolLambdaColumn<contact>>(
        prefix + "in_service_notification_period",
        "Wether the contact is currently in his/her service notification period (0/1)",
        offsets, [](const contact &ct) {
            return g_timeperiods_cache->inTimeperiod(
                ct.service_notification_period_ptr);
        }));
    table->addColumn(std::make_unique<ListLambdaColumn<contact>>(
        prefix + "custom_variable_names",
        "A list of all custom variables of the contact", offsets,
        GetCustomAttributeElem<0>{table->core(),
                                  AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<ListLambdaColumn<contact>>(
        prefix + "custom_variable_values",
        "A list of the values of all custom variables of the contact", offsets,
        GetCustomAttributeElem<1>{table->core(),
                                  AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<contact>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets,
        GetCustomAttribute{table->core(), AttributeKind::custom_variables}));

    table->addColumn(std::make_unique<ListLambdaColumn<contact>>(
        prefix + "tag_names", "A list of all tags of the contact", offsets,
        GetCustomAttributeElem<0>{table->core(), AttributeKind::tags}));
    table->addColumn(std::make_unique<ListLambdaColumn<contact>>(
        prefix + "tag_values",
        "A list of the values of all tags of the contact", offsets,
        GetCustomAttributeElem<1>{table->core(), AttributeKind::tags}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<contact>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        GetCustomAttribute{table->core(), AttributeKind::tags}));

    table->addColumn(std::make_unique<ListLambdaColumn<contact>>(
        prefix + "label_names", "A list of all labels of the contact", offsets,
        GetCustomAttributeElem<0>{table->core(), AttributeKind::labels}));
    table->addColumn(std::make_unique<ListLambdaColumn<contact>>(
        prefix + "label_values",
        "A list of the values of all labels of the contact", offsets,
        GetCustomAttributeElem<1>{table->core(), AttributeKind::labels}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<contact>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        GetCustomAttribute{table->core(), AttributeKind::labels}));

    table->addColumn(std::make_unique<ListLambdaColumn<contact>>(
        prefix + "label_source_names", "A list of all sources of the contact",
        offsets,
        GetCustomAttributeElem<0>{table->core(),
                                  AttributeKind::label_sources}));
    table->addColumn(std::make_unique<ListLambdaColumn<contact>>(
        prefix + "label_source_values",
        "A list of the values of all sources of the contact", offsets,
        GetCustomAttributeElem<1>{table->core(),
                                  AttributeKind::label_sources}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<contact>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        GetCustomAttribute{table->core(), AttributeKind::label_sources}));

    table->addColumn(std::make_unique<AttributeBitmaskLambdaColumn<contact>>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified", offsets,
        [](const contact &ct) { return ct.modified_attributes; }));
    table->addColumn(std::make_unique<AttributeListColumn2<contact>>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", offsets,
        AttributeBitmaskLambdaColumn<contact>{
            ""s, ""s, offsets,
            [](const contact &ct) { return ct.modified_attributes; }}));
}

void TableContacts::answerQuery(Query *query) {
    for (const contact *ct = contact_list; ct != nullptr; ct = ct->next) {
        if (!query->processDataset(Row{ct})) {
            break;
        }
    }
}

Row TableContacts::findObject(const std::string &objectspec) const {
    return Row(core()->find_contact(objectspec));
}
