// .------------------------------------------------------------------------.
// |                ____ _               _        __  __ _  __              |
// |               / ___| |__   ___  ___| | __   |  \/  | |/ /              |
// |              | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /               |
// |              | |___| | | |  __/ (__|   <    | |  | | . \               |
// |               \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\              |
// |                                        |_____|                         |
// |             _____       _                       _                      |
// |            | ____|_ __ | |_ ___ _ __ _ __  _ __(_)___  ___             |
// |            |  _| | '_ \| __/ _ \ '__| '_ \| '__| / __|/ _ \            |
// |            | |___| | | | ||  __/ |  | |_) | |  | \__ \  __/            |
// |            |_____|_| |_|\__\___|_|  | .__/|_|  |_|___/\___|            |
// |                                     |_|                                |
// |                     _____    _ _ _   _                                 |
// |                    | ____|__| (_) |_(_) ___  _ __                      |
// |                    |  _| / _` | | __| |/ _ \| '_ \                     |
// |                    | |__| (_| | | |_| | (_) | | | |                    |
// |                    |_____\__,_|_|\__|_|\___/|_| |_|                    |
// |                                                                        |
// | mathias-kettner.com                                 mathias-kettner.de |
// '------------------------------------------------------------------------'
//  This file is part of the Check_MK Enterprise Edition (CEE).
//  Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
//  Distributed under the Check_MK Enterprise License.
//
//  You should have  received  a copy of the Check_MK Enterprise License
//  along with Check_MK. If not, email to mk@mathias-kettner.de
//  or write to the postal address provided at www.mathias-kettner.de

#include "DynamicRRDColumn.h"
#include <cstdlib>
#include <stdexcept>
#include <vector>
#include "strutil.h"

DynamicRRDColumn::DynamicRRDColumn(const std::string &name,
                                   const std::string &description,
                                   MonitoringCore *mc,
                                   const Column::Offsets &offsets)
    : DynamicColumn(name, description, offsets), _mc(mc) {}

std::unique_ptr<Filter> DynamicRRDColumn::createFilter(
    RelationalOperator /*unused*/, const std::string & /*unused*/) const {
    throw std::runtime_error("filtering on dynamic RRD column '" + name() +
                             "' not supported");
}

[[nodiscard]] MonitoringCore *DynamicRRDColumn::core() { return _mc; }

DynamicRRDColumn::Args DynamicRRDColumn::parse_args(
    const std::string &arguments) const {
    // We expect the following arguments: RPN:START_TIME:END_TIME:RESOLUTION
    // Example: fs_used,1024,/:1426411073:1426416473:5
    std::vector<char> args(arguments.begin(), arguments.end());
    args.push_back('\0');
    char *scan = &args[0];

    // Reverse Polish Notation Expression for extraction start RRD
    char *rpn = next_token(&scan, ':');
    if (rpn == nullptr || rpn[0] == 0) {
        invalid("missing RPN expression for RRD");
    }

    // Start time of queried range - UNIX time stamp
    char *start_time = next_token(&scan, ':');
    if (start_time == nullptr || start_time[0] == 0 || atol(start_time) <= 0) {
        invalid("missing, negative or overflowed start time");
    }

    // End time - UNIX time stamp
    char *end_time = next_token(&scan, ':');
    if (end_time == nullptr || end_time[0] == 0 || atol(end_time) <= 0) {
        invalid(" missing, negative or overflowed end time");
    }

    // Resolution in seconds - might output less
    char *resolution = next_token(&scan, ':');
    if (resolution == nullptr || resolution[0] == 0 || atoi(resolution) <= 0) {
        invalid("missing or negative resolution");
    }

    // Optional limit of data points
    const char *max_entries = next_token(&scan, ':');
    if (max_entries == nullptr) {
        max_entries = "400";  // RRDTool default
    }

    if (max_entries[0] == 0 || atoi(max_entries) < 10) {
        invalid("Wrong input for max rows");
    }

    if (next_token(&scan, ':') != nullptr) {
        invalid("too many arguments");
    }
    return Args{rpn, atol(start_time), atol(end_time), atoi(resolution),
                atoi(max_entries)};
}

void DynamicRRDColumn::invalid(const std::string &message) const {
    throw std::runtime_error("invalid arguments for column '" + _name + ": " +
                             message);
}
