// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "TableEventConsole.h"

#include <chrono>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <iosfwd>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <unordered_set>
#include <utility>

#include "Column.h"
#include "DoubleColumn.h"
#include "EventConsoleConnection.h"
#include "Logger.h"
#include "Query.h"
#include "Row.h"
#include "StringColumn.h"
#include "StringUtils.h"
#include "TimeColumn.h"
#include "auth.h"

using namespace std::chrono_literals;

namespace {
// NOTE: Keep this in sync with EC code. Ugly...
const std::vector<std::string> grepping_filters = {
    "event_id",         "event_text",      "event_comment",     "event_host",
    "event_host_regex", "event_contact",   "event_application", "event_rule_id",
    "event_owner",      "event_ipaddress", "event_core_host"

};

class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(MonitoringCore *mc, const Table &table, Query &query,
                      const User &user,
                      std::function<bool(const User &, Row)> is_authorized)
        : EventConsoleConnection(mc->loggerLivestatus(),
                                 mc->mkeventdSocketPath())
        , mc_{mc}
        , table_{table}
        , query_{query}
        , user_{user}
        , is_authorized_{std::move(is_authorized)} {}

private:
    void sendRequest(std::ostream &os) override {
        os << std::nounitbuf;
        emitGET(os);
        emitOutputFormat(os);
        emitColumnsHeader(os);
        emitTimeRangeFilter(os);
        emitGreppingFilter(os);
        os << std::endl;
    }

    void emitGET(std::ostream &os) const {
        // skip "eventconsole" prefix :-P
        os << "GET " << table_.name().substr(12);
    }

    static void emitOutputFormat(std::ostream &os) {
        os << "\nOutputFormat: plain";
    }

    void emitColumnsHeader(std::ostream &os) {
        os << "\nColumns:";
        // Initially we consider all columns used in the query...
        auto all = query_.allColumns();
        // ... then we add some special columns which we might need irrespective
        // of the actual query...
        static std::unordered_set<std::string> special_columns{
            // see receiveReply
            "event_host",
            // see isAuthorizedForEvent
            "event_contact_groups_precedence",
            // see  isAuthorizedForEventViaContactGroups
            "event_contact_groups"};
        table_.any_column([&](const auto &col) {
            if (special_columns.find(col->name()) != special_columns.end()) {
                all.insert(col);
            }
            return false;
        });
        // .. and then we ignore all host-related columns, they are implicitly
        // joined later via ECRow._host later.
        for (const auto &c : all) {
            if (!mk::starts_with(c->name(), "host_")) {
                os << " " << c->name();
            }
        }
    }

    void emitTimeRangeFilter(std::ostream &os) {
        if (auto glb = query_.greatestLowerBoundFor("history_time")) {
            os << "\nFilter: history_time >= " << *glb;
        }
        if (auto lub = query_.leastUpperBoundFor("history_time")) {
            os << "\nFilter: history_time <= " << *lub;
        }
    }

    void emitGreppingFilter(std::ostream &os) {
        for (const auto &column_name : grepping_filters) {
            if (auto svr = query_.stringValueRestrictionFor(column_name)) {
                os << "\nFilter: " << column_name << " = " << *svr;
            } else {
                auto glb = query_.greatestLowerBoundFor(column_name);
                auto lub = query_.leastUpperBoundFor(column_name);
                if (glb && lub && glb == lub) {
                    os << "\nFilter: " << column_name << " = " << *glb;
                }
                // NOTE: We could emit >= or <= constraints for cases where we
                // know only one bound or the bounds are different, but the EC
                // can't make use of that currently.
            }
        }
    }

    void receiveReply(std::istream &is) override {
        bool is_header = true;
        std::vector<std::string> headers;
        do {
            std::string line;
            std::getline(is, line);
            if (!is || line.empty()) {
                return;
            }
            std::vector<std::string> columns = mk::split(line, '\t');
            if (is_header) {
                headers = std::move(columns);
                is_header = false;
            } else {
                ECRow row{mc_, headers, columns};
                if (is_authorized_(user_, Row{&row}) &&
                    !query_.processDataset(Row{&row})) {
                    return;
                }
            }
        } while (true);
    }

    MonitoringCore *mc_;
    const Table &table_;
    Query &query_;
    const User &user_;
    const std::function<bool(const User &, Row)> is_authorized_;
};
}  // namespace

ECRow::ECRow(MonitoringCore *mc, const std::vector<std::string> &headers,
             const std::vector<std::string> &columns) {
    auto column_it = columns.cbegin();
    for (const auto &header : headers) {
        if (column_it != columns.end()) {
            map_[header] = *column_it++;
        }
    }
    auto it = map_.find("event_host");
    host_ = it == map_.end() ? nullptr : mc->getHostByDesignation(it->second);
}

// static
std::unique_ptr<StringColumn<ECRow>> ECRow::makeStringColumn(
    const std::string &name, const std::string &description,
    const ColumnOffsets &offsets) {
    return std::make_unique<StringColumn<ECRow>>(
        name, description, offsets,
        [name](const ECRow &r) { return r.getString(name); });
}

// static
std::unique_ptr<IntColumn<ECRow>> ECRow::makeIntColumn(
    const std::string &name, const std::string &description,
    const ColumnOffsets &offsets) {
    return std::make_unique<IntColumn<ECRow>>(
        name, description, offsets,
        [name](const ECRow &r) { return r.getInt(name); });
}

// static
std::unique_ptr<DoubleColumn<ECRow>> ECRow::makeDoubleColumn(
    const std::string &name, const std::string &description,
    const ColumnOffsets &offsets) {
    return std::make_unique<DoubleColumn<ECRow>>(
        name, description, offsets,
        [name](const ECRow &r) { return r.getDouble(name); });
}

// static
std::unique_ptr<TimeColumn<ECRow>> ECRow::makeTimeColumn(
    const std::string &name, const std::string &description,
    const ColumnOffsets &offsets) {
    return std::make_unique<TimeColumn<ECRow>>(
        name, description, offsets, [name](const ECRow &r) {
            return std::chrono::system_clock::from_time_t(
                static_cast<std::time_t>(r.getDouble(name)));
        });
}

// static
std::unique_ptr<ListColumn<ECRow>> ECRow::makeListColumn(
    const std::string &name, const std::string &description,
    const ColumnOffsets &offsets) {
    return std::make_unique<ListColumn<ECRow>>(
        name, description, offsets, [name](const ECRow &r) {
            auto result = r.getString(name);
            return result.empty() || result == "\002"
                       ? std::vector<std::string>()
                       : mk::split(result.substr(1), '\001');
        });
}

std::string ECRow::getString(const std::string &column_name) const {
    return get(column_name, "");
}

int32_t ECRow::getInt(const std::string &column_name) const {
    return static_cast<int32_t>(atol(get(column_name, "0").c_str()));
}

double ECRow::getDouble(const std::string &column_name) const {
    return atof(get(column_name, "0").c_str());
}

std::string ECRow::get(const std::string &column_name,
                       const std::string &default_value) const {
    auto it = map_.find(column_name);
    return it == map_.end() ? default_value : it->second;
}

const MonitoringCore::Host *ECRow::host() const { return host_; }

TableEventConsole::TableEventConsole(
    MonitoringCore *mc, std::function<bool(const User &, Row)> is_authorized)
    : Table{mc}, is_authorized_{std::move(is_authorized)} {}

void TableEventConsole::answerQuery(Query &query, const User &user) {
    if (core()->mkeventdEnabled()) {
        try {
            ECTableConnection{core(), *this, query, user, is_authorized_}.run();
        } catch (const std::runtime_error &err) {
            query.badGateway(err.what());
        }
    }
}

bool TableEventConsole::isAuthorizedForEvent(const User &user, Row row) const {
    if (user.is_authorized_for_everything()) {
        return true;
    }
    // NOTE: Further filtering in the GUI for mkeventd.seeunrelated permission
    bool result = true;
    auto precedence = std::static_pointer_cast<StringColumn<ECRow>>(
                          column("event_contact_groups_precedence"))
                          ->getValue(row);
    if (precedence == "rule") {
        isAuthorizedForEventViaContactGroups(user, row, result) ||
            isAuthorizedForEventViaHost(user, row, result);
    } else if (precedence == "host") {
        isAuthorizedForEventViaHost(user, row, result) ||
            isAuthorizedForEventViaContactGroups(user, row, result);
    } else {
        Error(logger()) << "unknown precedence '" << precedence << "' in table "
                        << name();
        result = false;
    }
    return result;
}

bool TableEventConsole::isAuthorizedForEventViaContactGroups(
    const User &user, Row row, bool &result) const {
    auto col = std::static_pointer_cast<ListColumn<ECRow>>(
        column("event_contact_groups"));
    if (const auto *r = col->columnData<ECRow>(row)) {
        // TODO(sp) This check for None is a hack...
        if (r->getString(col->name()) == "\002") {
            return false;
        }
    }
    for (const auto &name : col->getValue(row, unknown_auth_user(), 0s)) {
        if (core()->is_contact_member_of_contactgroup(
                core()->find_contactgroup(name),
                reinterpret_cast<const MonitoringCore::Contact *>(
                    user.authUser()))) {
            return (result = true, true);
        }
    }
    return (result = false, true);
}

bool TableEventConsole::isAuthorizedForEventViaHost(const User &user, Row row,
                                                    bool &result) const {
    if (const MonitoringCore::Host *hst = rowData<ECRow>(row)->host()) {
        return (result = core()->host_has_contact(
                    hst, reinterpret_cast<const MonitoringCore::Contact *>(
                             user.authUser())),
                true);
    }
    return false;
}
