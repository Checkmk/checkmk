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

#include "DynamicEventConsoleReplicationColumn.h"
#include <iosfwd>
#include <memory>
#include <utility>
#include <vector>
#include "BlobColumn.h"
#include "Column.h"
#include "EventConsoleConnection.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "Row.h"

using std::make_unique;
using std::move;
using std::string;
using std::unique_ptr;
using std::vector;

namespace {
class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(MonitoringCore *mc, string command)
        : EventConsoleConnection(mc->loggerLivestatus(),
                                 mc->mkeventdSocketPath())
        , _command(move(command)) {}
    string getResult() const { return _result; }

private:
    void sendRequest(std::ostream &os) override { os << _command; }
    bool receiveReply() override { return getline(_result); }

    const string _command;
    string _result;
};

class ReplicationColumn : public BlobColumn {
public:
    ReplicationColumn(string name, string description, string blob,
                      int indirect_offset, int extra_offset,
                      int extra_extra_offset)
        : BlobColumn(name, description, indirect_offset, extra_offset,
                     extra_extra_offset)
        , _blob(move(blob)) {}

    unique_ptr<vector<char>> getBlob(Row /* unused */) override {
        return make_unique<vector<char>>(_blob.begin(), _blob.end());
    };

private:
    const string _blob;
};
}  // namespace

DynamicEventConsoleReplicationColumn::DynamicEventConsoleReplicationColumn(
    const std::string &name, const std::string &description, MonitoringCore *mc,
    int indirect_offset, int extra_offset, int extra_extra_offset)
    : DynamicColumn(name, description, mc->loggerLivestatus(), indirect_offset,
                    extra_offset, extra_extra_offset)
    , _mc(mc) {}

unique_ptr<Column> DynamicEventConsoleReplicationColumn::createColumn(
    const std::string &name, const std::string &arguments) {
    string result;
    if (_mc->mkeventdEnabled()) {
        try {
            ECTableConnection ec(_mc, "REPLICATE " + arguments);
            ec.run();
            result = ec.getResult();
        } catch (const generic_error &ge) {
            // Nothing to do here, returning an empty result is OK.
        }
    }
    return make_unique<ReplicationColumn>(name, "replication value", result, -1,
                                          -1, -1);
}
