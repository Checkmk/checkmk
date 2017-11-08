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

#include "TableEventConsole.h"
#include <ctime>
#include <iosfwd>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <utility>
#include "Column.h"
#include "EventConsoleConnection.h"
#include "Logger.h"
#include "Query.h"

namespace {
class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(MonitoringCore *mc, std::string table_name, Query *query)
        : EventConsoleConnection(mc->loggerLivestatus(),
                                 mc->mkeventdSocketPath())
        , _mc(mc)
        , _table_name(move(table_name))
        , _query(query) {}

private:
    void sendRequest(std::ostream &os) override {
        // NOTE: The EC ignores Columns: at the moment!
        os << std::nounitbuf << "GET " << _table_name
           << "\nOutputFormat: plain\nColumns:";
        for (const auto &c : _query->allColumns()) {
            if (!mk::starts_with(c->name(), "host_")) {
                os << " " << c->name();
            }
        }
        // HACK: Reconstruct time range filter
        auto end = time(nullptr) + 1;
        int since = 0;
        int until = end;
        _query->findIntLimits("history_time", &since, &until);
        if (since != 0) {
            os << "\nFilter: history_time >= " << since;
        }
        if (until != end) {
            os << "\nFilter: history_time <= " << until - 1;
        }
        os << std::endl;
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
                TableEventConsole::ECRow row;
                int i = 0;
                columns.resize(headers.size());  // just to be sure...
                for (const auto &field : columns) {
                    row._map[headers[i++]] = field;
                }

                auto it = row._map.find("event_host");
                row._host = it == row._map.end()
                                ? nullptr
                                : _mc->getHostByDesignation(it->second);
                _query->processDataset(Row(&row));
            }
        } while (true);
    }

    MonitoringCore *_mc;
    std::string _table_name;
    Query *_query;
};
}  // namespace

TableEventConsole::TableEventConsole(MonitoringCore *mc) : Table(mc) {}

void TableEventConsole::answerQuery(Query *query) {
    if (core()->mkeventdEnabled()) {
        try {
            // skip "eventconsole" prefix :-P
            ECTableConnection(core(), name().substr(12), query).run();
        } catch (const std::runtime_error &err) {
            query->invalidRequest(err.what());
        }
    }
}

bool TableEventConsole::isAuthorizedForEvent(Row row, contact *ctc) {
    // TODO(sp) Remove evil casts below.
    auto c = reinterpret_cast<MonitoringCore::Contact *>(ctc);
    auto r = rowData<ECRow>(row);
    // NOTE: Further filtering in the GUI for mkeventd.seeunrelated permission
    bool result = true;
    auto precedence = std::static_pointer_cast<StringEventConsoleColumn>(
                          column("event_contact_groups_precedence"))
                          ->getValue(row);
    if (precedence == "rule") {
        isAuthorizedForEventViaContactGroups(c, r, result) ||
            isAuthorizedForEventViaHost(c, r, result);
    } else if (precedence == "host") {
        isAuthorizedForEventViaHost(c, r, result) ||
            isAuthorizedForEventViaContactGroups(c, r, result);
    } else {
        Error(logger()) << "unknown precedence '" << precedence << "' in table "
                        << name();
        result = false;
    }
    return result;
}

bool TableEventConsole::isAuthorizedForEventViaContactGroups(
    MonitoringCore::Contact *ctc, ECRow *row, bool &result) {
    auto col = std::static_pointer_cast<ListEventConsoleColumn>(
        column("event_contact_groups"));
    if (col->isNone(row)) {
        return false;
    }
    for (const auto &name : col->getValue(Row(row))) {
        if (core()->is_contact_member_of_contactgroup(
                core()->find_contactgroup(name), ctc)) {
            return (result = true, true);
        }
    }
    return (result = false, true);
}

bool TableEventConsole::isAuthorizedForEventViaHost(
    MonitoringCore::Contact *ctc, ECRow *row, bool &result) {
    if (MonitoringCore::Host *hst = row->_host) {
        return (result = core()->host_has_contact(hst, ctc), true);
    }
    return false;
}
