// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "TableContacts.h"
#include <algorithm>
#include <iosfwd>
#include <iterator>
#include <memory>
#include <string_view>
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

// The fuchsia-trailing-return warning are all false positives.
template <typename Member, typename Default>
class GetAttr {  // NOLINT(fuchsia-trailing-return)
public:
    // NOLINTNEXTLINE(fuchsia-trailing-return)
    GetAttr(Member contact::*m, Default d) : m_{m}, d_{std::move(d)} {}
    Default operator()(Row row) {
        auto r = row.rawData<Table::IRow>();
        if (auto ct =
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
    Default operator()(Row row) {
        auto r = row.rawData<Table::IRow>();
        if (auto ct =
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
class GetTimePeriod {  // NOLINT(fuchsia-trailing-return)
public:
    // NOLINTNEXTLINE(fuchsia-trailing-return)
    GetTimePeriod(Member *contact::*m, bool d) : m_{m}, d_{d} {}
    bool operator()(Row row) {
        auto r = row.rawData<Table::IRow>();
        if (auto ct =
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
    Attributes operator()(Row row) {
        auto r = row.rawData<Table::IRow>();
        if (auto ct =
                dynamic_cast<const TableContacts::IRow *>(r)->getContact()) {
            if (auto p = ct->custom_variables) {
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
    std::vector<std::string> operator()(Row row) {
        auto attrs = get_attrs_(row);
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
    addColumns(this, "");
}

std::string TableContacts::name() const { return "contacts"; }

std::string TableContacts::namePrefix() const { return "contact_"; }

// static
void TableContacts::addColumns(Table *table, const std::string &prefix) {
    table->addColumn(std::make_unique<StringLambdaColumn>(
        prefix + "name", "The login name of the contact person",
        GetAttr(&contact::name, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn>(
        prefix + "alias", "The full name of the contact",
        GetAttr(&contact::alias, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn>(
        prefix + "email", "The email address of the contact",
        GetAttr(&contact::email, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn>(
        prefix + "pager", "The pager address of the contact",
        GetAttr(&contact::pager, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn>(
        prefix + "host_notification_period",
        "The time period in which the contact will be notified about host problems",
        GetAttr(&contact::host_notification_period, ""s)));
    table->addColumn(std::make_unique<StringLambdaColumn>(
        prefix + "service_notification_period",
        "The time period in which the contact will be notified about service problems",
        GetAttr(&contact::service_notification_period, ""s)));
    for (int i = 0; i < MAX_CONTACT_ADDRESSES; ++i) {
        std::string b = "address" + std::to_string(i + 1);
        table->addColumn(std::make_unique<StringLambdaColumn>(
            prefix + b, "The additional field " + b,
            [i](Row row) -> std::string {
                auto r = row.rawData<Table::IRow>();
                if (auto ct = dynamic_cast<const IRow *>(r)->getContact()) {
                    return ct->address[i] == nullptr ? ""s : ct->address[i];
                }
                return ""s;
            }));
    }

    table->addColumn(std::make_unique<IntLambdaColumn>(
        prefix + "can_submit_commands",
        "Wether the contact is allowed to submit commands (0/1)",
        GetAttr(&contact::can_submit_commands, 0)));
    table->addColumn(std::make_unique<IntLambdaColumn>(
        prefix + "host_notifications_enabled",
        "Wether the contact will be notified about host problems in general (0/1)",
        GetAttr(&contact::host_notifications_enabled, 0)));
    table->addColumn(std::make_unique<IntLambdaColumn>(
        prefix + "service_notifications_enabled",
        "Wether the contact will be notified about service problems in general (0/1)",
        GetAttr(&contact::service_notifications_enabled, 0)));
    table->addColumn(std::make_unique<BoolLambdaColumn>(
        prefix + "in_host_notification_period",
        "Wether the contact is currently in his/her host notification period (0/1)",
        GetTimePeriod(&contact::host_notification_period_ptr, false)));
    table->addColumn(std::make_unique<BoolLambdaColumn>(
        prefix + "in_service_notification_period",
        "Wether the contact is currently in his/her service notification period (0/1)",
        GetTimePeriod(&contact::service_notification_period_ptr, false)));
    table->addColumn(std::make_unique<ListLambdaColumn>(
        prefix + "custom_variable_names",
        "A list of all custom variables of the contact",
        GetCustomAttributeElem<0>{table->core(),
                                  AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<ListLambdaColumn>(
        prefix + "custom_variable_values",
        "A list of the values of all custom variables of the contact",
        GetCustomAttributeElem<1>{table->core(),
                                  AttributeKind::custom_variables}));
    table->addColumn(std::make_unique<AttributesLambdaColumn>(
        prefix + "custom_variables", "A dictionary of the custom variables",
        GetCustomAttribute{table->core(), AttributeKind::custom_variables}));

    table->addColumn(std::make_unique<ListLambdaColumn>(
        prefix + "tag_names", "A list of all tags of the contact",
        GetCustomAttributeElem<0>{table->core(), AttributeKind::tags}));
    table->addColumn(std::make_unique<ListLambdaColumn>(
        prefix + "tag_values",
        "A list of the values of all tags of the contact",
        GetCustomAttributeElem<1>{table->core(), AttributeKind::tags}));
    table->addColumn(std::make_unique<AttributesLambdaColumn>(
        prefix + "tags", "A dictionary of the tags",
        GetCustomAttribute{table->core(), AttributeKind::tags}));

    table->addColumn(std::make_unique<ListLambdaColumn>(
        prefix + "label_names", "A list of all labels of the contact",
        GetCustomAttributeElem<0>{table->core(), AttributeKind::labels}));
    table->addColumn(std::make_unique<ListLambdaColumn>(
        prefix + "label_values",
        "A list of the values of all labels of the contact",
        GetCustomAttributeElem<1>{table->core(), AttributeKind::labels}));
    table->addColumn(std::make_unique<AttributesLambdaColumn>(
        prefix + "labels", "A dictionary of the labels",
        GetCustomAttribute{table->core(), AttributeKind::labels}));

    table->addColumn(std::make_unique<ListLambdaColumn>(
        prefix + "label_source_names", "A list of all sources of the contact",
        GetCustomAttributeElem<0>{table->core(),
                                  AttributeKind::label_sources}));
    table->addColumn(std::make_unique<ListLambdaColumn>(
        prefix + "label_source_values",
        "A list of the values of all sources of the contact",
        GetCustomAttributeElem<1>{table->core(),
                                  AttributeKind::label_sources}));
    table->addColumn(std::make_unique<AttributesLambdaColumn>(
        prefix + "label_sources", "A dictionary of the label sources",
        GetCustomAttribute{table->core(), AttributeKind::label_sources}));

    table->addColumn(std::make_unique<AttributeBitmaskLambdaColumn>(
        prefix + "modified_attributes",
        "A bitmask specifying which attributes have been modified",
        GetAttr{&contact::modified_attributes, 0}));
    table->addColumn(std::make_unique<AttributeListColumn2>(
        prefix + "modified_attributes_list",
        "A list of all modified attributes",
        AttributeBitmaskLambdaColumn{
            ""s, ""s, GetAttr{&contact::modified_attributes, 0}}));
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
