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

class ContactRow : public TableContacts::IRow {
public:
    explicit ContactRow(contact *ct) : contact_{ct} {};
    [[nodiscard]] const contact *getContact() const override {
        return contact_;
    }

private:
    const contact *contact_;
};

template <typename Member, typename Default>
class GetAttr {
public:
    GetAttr(Member contact::*m, Default d) : m_{m}, d_{std::move(d)} {}
    Default operator()(const Table::IRow *r) {
        if (const auto *ct =
                dynamic_cast<const TableContacts::IRow *>(r)->getContact()) {
            return ct->*m_;
        }
        return d_;
    }

private:
    Member contact::*m_;
    Default d_;
};

// Specialization on Member*: Check if pointer members are nullptr.
template <typename Member, typename Default>
class GetAttr<Member *, Default> {
public:
    GetAttr(Member *contact::*m, Default d) : m_{m}, d_{std::move(d)} {}
    Default operator()(const Table::IRow *r) {
        if (const auto *ct =
                dynamic_cast<const TableContacts::IRow *>(r)->getContact()) {
            return ct->*m_ == nullptr ? d_ : ct->*m_;
        }
        return d_;
    }

private:
    Member *contact::*m_;
    Default d_;
};

template <typename Member>
class GetTimePeriod {
public:
    GetTimePeriod(Member *contact::*m, bool d) : m_{m}, d_{d} {}
    bool operator()(const Table::IRow *r) {
        if (const auto *ct =
                dynamic_cast<const TableContacts::IRow *>(r)->getContact()) {
            return g_timeperiods_cache->inTimeperiod(ct->*m_);
        }
        return d_;
    }

private:
    Member *contact::*m_;
    bool d_;
};

class GetCustomAttribute {
public:
    GetCustomAttribute(const MonitoringCore *const mc, const AttributeKind kind)
        : mc_{mc}, kind_{kind} {}
    Attributes operator()(const Table::IRow *r) {
        if (const auto *ct =
                dynamic_cast<const TableContacts::IRow *>(r)->getContact()) {
            if (const auto *p = ct->custom_variables) {
                return mc_->customAttributes(&p, kind_);
            }
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
    std::vector<std::string> operator()(const Table::IRow *r) {
        auto attrs = get_attrs_(r);
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
    addColumns(this, "", 0);
}

std::string TableContacts::name() const { return "contacts"; }

std::string TableContacts::namePrefix() const { return "contact_"; }

// static
void TableContacts::addColumns(Table *table, const std::string &prefix,
                               int /*indirect_offset*/) {
    Column::Offsets offsets{};
    table->addColumn(std::make_unique<StringLambdaColumn<Table::IRow>>(
        prefix + "name", "The login name of the contact person", offsets,
        GetAttr(&contact::name, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn<Table::IRow>>(
        prefix + "alias", "The full name of the contact", offsets,
        GetAttr(&contact::alias, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn<Table::IRow>>(
        prefix + "email", "The email address of the contact", offsets,
        GetAttr(&contact::email, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn<Table::IRow>>(
        prefix + "pager", "The pager address of the contact", offsets,
        GetAttr(&contact::pager, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn<Table::IRow>>(
        prefix + "host_notification_period",
        "The time period in which the contact will be notified about host problems",
        offsets, GetAttr(&contact::host_notification_period, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn<Table::IRow>>(
        prefix + "service_notification_period",
        "The time period in which the contact will be notified about service problems",
        offsets, GetAttr(&contact::service_notification_period, ""s)));
    for (int i = 0; i < MAX_CONTACT_ADDRESSES; ++i) {
        std::string b = "address" + std::to_string(i + 1);
        table->addColumn(std::make_unique<StringLambdaColumn<Table::IRow>>(
            prefix + b, "The additional field " + b, offsets,
            [i](const Table::IRow *r) -> std::string {
                if (const auto *ct =
                        dynamic_cast<const IRow *>(r)->getContact()) {
                    return ct->address[i] == nullptr ? ""s : ct->address[i];
                }
                return ""s;
            }));
    }

    table->addColumn(std::make_unique<IntLambdaColumn<Table::IRow>>(
        prefix + "can_submit_commands",
        "Wether the contact is allowed to submit commands (0/1)", offsets,
        GetAttr(&contact::can_submit_commands, 0)));
    table->addColumn(std::make_unique<IntLambdaColumn<Table::IRow>>(
        prefix + "host_notifications_enabled",
        "Wether the contact will be notified about host problems in general (0/1)",
        offsets, GetAttr(&contact::host_notifications_enabled, 0)));
    table->addColumn(std::make_unique<IntLambdaColumn<Table::IRow>>(
        prefix + "service_notifications_enabled",
        "Wether the contact will be notified about service problems in general (0/1)",
        offsets, GetAttr(&contact::service_notifications_enabled, 0)));
    table->addColumn(std::make_unique<BoolLambdaColumn<Table::IRow>>(
        prefix + "in_host_notification_period",
        "Wether the contact is currently in his/her host notification period (0/1)",
        offsets, GetTimePeriod(&contact::host_notification_period_ptr, false)));
    table->addColumn(std::make_unique<BoolLambdaColumn<Table::IRow>>(
        prefix + "in_service_notification_period",
        "Wether the contact is currently in his/her service notification period (0/1)",
        offsets,
        GetTimePeriod(&contact::service_notification_period_ptr, false)));
    table->addColumn(std::make_unique<ListLambdaColumn<Table::IRow>>(
        prefix + "custom_variable_names",
        "A list of all custom variables of the contact", offsets,
        GetCustomAttributeElem<0>{table->core(),
                                  AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<ListLambdaColumn<Table::IRow>>(
        prefix + "custom_variable_values",
        "A list of the values of all custom variables of the contact", offsets,
        GetCustomAttributeElem<1>{table->core(),
                                  AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<Table::IRow>>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        offsets,
        GetCustomAttribute{table->core(), AttributeKind::custom_variables}));

    table->addColumn(std::make_unique<ListLambdaColumn<Table::IRow>>(
        prefix + "tag_names", "A list of all tags of the contact", offsets,
        GetCustomAttributeElem<0>{table->core(), AttributeKind::tags}));
    table->addColumn(std::make_unique<ListLambdaColumn<Table::IRow>>(
        prefix + "tag_values",
        "A list of the values of all tags of the contact", offsets,
        GetCustomAttributeElem<1>{table->core(), AttributeKind::tags}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<Table::IRow>>(
        prefix + "tags", "A dictionary of the tags", offsets,
        GetCustomAttribute{table->core(), AttributeKind::tags}));

    table->addColumn(std::make_unique<ListLambdaColumn<Table::IRow>>(
        prefix + "label_names", "A list of all labels of the contact", offsets,
        GetCustomAttributeElem<0>{table->core(), AttributeKind::labels}));
    table->addColumn(std::make_unique<ListLambdaColumn<Table::IRow>>(
        prefix + "label_values",
        "A list of the values of all labels of the contact", offsets,
        GetCustomAttributeElem<1>{table->core(), AttributeKind::labels}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<Table::IRow>>(
        prefix + "labels", "A dictionary of the labels", offsets,
        GetCustomAttribute{table->core(), AttributeKind::labels}));

    table->addColumn(std::make_unique<ListLambdaColumn<Table::IRow>>(
        prefix + "label_source_names", "A list of all sources of the contact",
        offsets,
        GetCustomAttributeElem<0>{table->core(),
                                  AttributeKind::label_sources}));
    table->addColumn(std::make_unique<ListLambdaColumn<Table::IRow>>(
        prefix + "label_source_values",
        "A list of the values of all sources of the contact", offsets,
        GetCustomAttributeElem<1>{table->core(),
                                  AttributeKind::label_sources}));
    table->addColumn(std::make_unique<AttributesLambdaColumn<Table::IRow>>(
        prefix + "label_sources", "A dictionary of the label sources", offsets,
        GetCustomAttribute{table->core(), AttributeKind::label_sources}));

    table->addColumn(
        std::make_unique<AttributeBitmaskLambdaColumn<Table::IRow>>(
            prefix + "modified_attributes",
            "A bitmask specifying which attributes have been modified", offsets,
            GetAttr{&contact::modified_attributes, 0}));
    table->addColumn(std::make_unique<AttributeListColumn2<Table::IRow>>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes", offsets,
        AttributeBitmaskLambdaColumn<Table::IRow>{
            ""s, ""s, offsets, GetAttr{&contact::modified_attributes, 0}}));
}

void TableContacts::answerQuery(Query *query) {
    for (contact *ct = contact_list; ct != nullptr; ct = ct->next) {
        auto r = ContactRow{ct};
        if (!query->processDataset(Row{dynamic_cast<Table::IRow *>(&r)})) {
            break;
        }
    }
}

Row TableContacts::findObject(const std::string &objectspec) const {
    return Row(core()->find_contact(objectspec));
}
