// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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
