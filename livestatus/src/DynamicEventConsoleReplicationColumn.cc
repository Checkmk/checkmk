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
#include <stdexcept>
#include <utility>
#include <vector>
#include "BlobColumn.h"
#include "Column.h"
#include "EventConsoleConnection.h"
#include "Logger.h"
#include "MonitoringCore.h"
#include "Row.h"

namespace {
class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(MonitoringCore *mc, std::string command)
        : EventConsoleConnection(mc->loggerLivestatus(),
                                 mc->mkeventdSocketPath())
        , command_(std::move(command)) {}
    [[nodiscard]] std::string getResult() const { return result_; }

private:
    void sendRequest(std::ostream &os) override { os << command_; }
    void receiveReply(std::istream &is) override { std::getline(is, result_); }

    std::string command_;
    std::string result_;
};

class ReplicationColumn : public BlobColumn {
public:
    ReplicationColumn(const std::string &name, const std::string &description,
                      std::string blob, int indirect_offset, int extra_offset,
                      int extra_extra_offset, int offset)
        : BlobColumn(name, description, indirect_offset, extra_offset,
                     extra_extra_offset, offset)
        , blob_(std::move(blob)) {}

    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row /* unused */) const override {
        return std::make_unique<std::vector<char>>(blob_.begin(), blob_.end());
    };

private:
    std::string blob_;
};
}  // namespace

DynamicEventConsoleReplicationColumn::DynamicEventConsoleReplicationColumn(
    const std::string &name, const std::string &description, MonitoringCore *mc,
    int indirect_offset, int extra_offset, int extra_extra_offset)
    : DynamicColumn(name, description, indirect_offset, extra_offset,
                    extra_extra_offset)
    , _mc(mc) {}

std::unique_ptr<Column> DynamicEventConsoleReplicationColumn::createColumn(
    const std::string &name, const std::string &arguments) {
    std::string result;
    if (_mc->mkeventdEnabled()) {
        try {
            ECTableConnection ec(_mc, "REPLICATE " + arguments);
            ec.run();
            result = ec.getResult();
        } catch (const std::runtime_error &err) {
            Alert(_mc->loggerLivestatus()) << err.what();
        }
    }
    return std::make_unique<ReplicationColumn>(name, "replication value",
                                               result, -1, -1, -1, 0);
}
