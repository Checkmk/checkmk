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
#include "EventConsoleConnection.h"
#ifdef CMC
#include "Config.h"
#include "Core.h"
#include "World.h"
#else
extern char g_mkeventd_socket_path[4096];
#endif

using std::make_unique;
using std::move;
using std::string;
using std::unique_ptr;
using std::vector;

namespace {
class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(Logger *logger, string path, string command)
        : EventConsoleConnection(logger, path), _command(move(command)) {}
    string getResult() const { return _result; }

private:
    void sendRequest(std::ostream &os) override { os << _command; }
    bool receiveReply() override { return getline(_result); }

    const string _command;
    string _result;
};

class ReplicationColumn : public BlobColumn {
public:
    ReplicationColumn(string name, string description, int indirect_offset,
                      int extra_offset, string blob)
        : BlobColumn(name, description, indirect_offset, extra_offset)
        , _blob(move(blob)) {}

    unique_ptr<vector<char>> getBlob(void * /* unused */) override {
        return make_unique<vector<char>>(_blob.begin(), _blob.end());
    };

private:
    const string _blob;
};
}  // namespace

DynamicEventConsoleReplicationColumn::DynamicEventConsoleReplicationColumn(
    const std::string &name, const std::string &description,
    int indirect_offset, int extra_offset, Logger *logger
#ifdef CMC
    ,
    Core *core
#endif
    )
    : DynamicColumn(name, description, indirect_offset, extra_offset, logger)
#ifdef CMC
    , _core(core)
#endif
{
}

Column *DynamicEventConsoleReplicationColumn::createColumn(
    const std::string &name, const std::string &arguments) {
#ifdef CMC
    string path = _core->_world->_config->_mkeventd_socket_path;
#else
    string path = g_mkeventd_socket_path;
#endif
    ECTableConnection ec(_logger, path, "REPLICATE " + arguments);
    ec.run();
    return new ReplicationColumn(name, "replication value", -1, -1,
                                 ec.getResult());
}
