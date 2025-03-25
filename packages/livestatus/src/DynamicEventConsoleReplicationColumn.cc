// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/DynamicEventConsoleReplicationColumn.h"

#include <filesystem>
#include <iosfwd>
#include <iterator>
#include <memory>
#include <ostream>
#include <stdexcept>
#include <type_traits>
#include <utility>
#include <vector>

#include "livestatus/BlobColumn.h"
#include "livestatus/Column.h"
#include "livestatus/EventConsoleConnection.h"
#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"

class TableEventConsoleReplication;

namespace {
class ECTableConnection : public EventConsoleConnection {
public:
    ECTableConnection(Logger *logger, std::string path, std::string command)
        : EventConsoleConnection(logger, std::move(path))
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
    const std::string &name, const std::string &description, ICore *mc,
    const ColumnOffsets &offsets)
    : DynamicColumn(name, description, offsets), _mc(mc) {}

std::unique_ptr<Column> DynamicEventConsoleReplicationColumn::createColumn(
    const std::string &name, const std::string &arguments) {
    std::string result;
    if (_mc->mkeventdEnabled()) {
        auto command = "REPLICATE " + arguments;
        try {
            ECTableConnection ec(_mc->loggerLivestatus(),
                                 _mc->paths()->event_console_status_socket(),
                                 command);
            ec.run();
            result = ec.getResult();
        } catch (const std::runtime_error &err) {
            Alert(_mc->loggerLivestatus()) << err.what();
        }
    }
    // TODO(sp) Using TableEventConsoleReplication here is a cruel hack,
    // DynamicEventConsoleReplicationColumn should really be a template.
    return std::make_unique<BlobColumn<TableEventConsoleReplication>>(
        name, "replication value", _offsets,
        [result =
             std::move(result)](const TableEventConsoleReplication & /*r*/) {
            return std::vector<char>{std::begin(result), std::end(result)};
        });
}
