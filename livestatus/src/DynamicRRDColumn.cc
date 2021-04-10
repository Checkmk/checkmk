// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DynamicRRDColumn.h"

#include <cstdlib>
#include <vector>

#include "strutil.h"

RRDColumnArgs::RRDColumnArgs(const std::string &arguments,
                             const std::string &column_name) {
    auto invalid = [&column_name](const std::string &message) {
        throw std::runtime_error("invalid arguments for column '" +
                                 column_name + ": " + message);
    };
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
    this->rpn = rpn;

    // Start time of queried range - UNIX time stamp
    char *start_time = next_token(&scan, ':');
    if (start_time == nullptr || start_time[0] == 0 || atol(start_time) <= 0) {
        invalid("missing, negative or overflowed start time");
    }
    this->start_time = atol(start_time);

    // End time - UNIX time stamp
    char *end_time = next_token(&scan, ':');
    if (end_time == nullptr || end_time[0] == 0 || atol(end_time) <= 0) {
        invalid(" missing, negative or overflowed end time");
    }
    this->end_time = atol(end_time);

    // Resolution in seconds - might output less
    char *resolution = next_token(&scan, ':');
    if (resolution == nullptr || resolution[0] == 0 || atoi(resolution) <= 0) {
        invalid("missing or negative resolution");
    }
    this->resolution = atoi(resolution);

    // Optional limit of data points
    const char *max_entries = next_token(&scan, ':');
    if (max_entries == nullptr) {
        max_entries = "400";  // RRDTool default
    }
    if (max_entries[0] == 0 || atoi(max_entries) < 10) {
        invalid("Wrong input for max rows");
    }
    this->max_entries = atoi(max_entries);

    if (next_token(&scan, ':') != nullptr) {
        invalid("too many arguments");
    }
}
