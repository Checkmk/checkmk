// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DynamicEventConsoleReplicationColumn.h"

#include <filesystem>
#include <iosfwd>
#include <iterator>
#include <stdexcept>
#include <utility>
#include <vector>

#include "BlobColumn.h"
#include "Column.h"
#include "EventConsoleConnection.h"
#include "Logger.h"
#include "MonitoringCore.h"
class Row;

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

}  // namespace

DynamicEventConsoleReplicationColumn::DynamicEventConsoleReplicationColumn(
    const std::string &name, const std::string &description, MonitoringCore *mc,
    const ColumnOffsets &offsets)
    : DynamicColumn(name, description, offsets), _mc(mc) {}

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
    return std::make_unique<BlobColumn<Row>::Constant>(
        name, "replication value",
        std::vector<char>{std::begin(result), std::end(result)});
}
