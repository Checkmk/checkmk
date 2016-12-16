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

// IWYU pragma: no_include <bits/shared_ptr.h>
#include "TableEventConsole.h"
#include <iosfwd>
#include <iostream>
#include <utility>
#include "Column.h"
#include "EventConsoleConnection.h"
#include "Query.h"

using std::ostream;
using std::string;
using std::vector;

namespace {
class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(MonitoringCore *core, string table_name, Query *query)
        : EventConsoleConnection(core->loggerLivestatus(),
                                 core->mkeventdSocketPath())
        , _core(core)
        , _table_name(move(table_name))
        , _query(query) {}

private:
    void sendRequest(std::ostream &os) override {
        // NOTE: The EC ignores Columns: at the moment!
        os << std::nounitbuf << "GET " << _table_name
           << "\nOutputFormat: plain\nColumns:";
        for (const auto &c : _query->allColumns()) {
            os << " " << c->name();
        }
        os << std::endl;
    }

    bool receiveReply() override {
        bool is_header = true;
        vector<string> headers;
        do {
            string line;
            if (!getline(line)) {
                return false;
            }
            if (line.empty()) {
                return true;
            }
            vector<string> columns = mk::split(line, '\t');
            if (is_header) {
                headers = std::move(columns);
                is_header = false;
            } else {
                TableEventConsole::Row row;
                int i = 0;
                columns.resize(headers.size());  // just to be sure...
                for (const auto &field : columns) {
                    row._map[headers[i++]] = field;
                }

                auto it = row._map.find("event_host");
                row._host = it == row._map.end()
                                ? nullptr
                                : _core->getHostByDesignation(it->second);
                _query->processDataset(&row);
            }
        } while (true);
        return true;
    }

    MonitoringCore *_core;
    std::string _table_name;
    Query *_query;
};
}  // namespace

TableEventConsole::TableEventConsole(MonitoringCore *core)
    : Table(core->loggerLivestatus()), _core(core) {}

void TableEventConsole::answerQuery(Query *query) {
    if (_core->mkeventdEnabled()) {
        try {
            // skip "eventconsole" prefix :-P
            ECTableConnection(_core, name().substr(12), query).run();
        } catch (const generic_error &ge) {
            query->invalidRequest(ge.what());
        }
    }
}
