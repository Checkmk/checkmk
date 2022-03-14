// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Metric.h"

#include <fstream>
#include <regex>
#include <sstream>

#include "Logger.h"

namespace {
const std::regex label_regex{
    R"(\s+<LABEL>(.+)</LABEL>)",
    std::regex_constants::ECMAScript | std::regex_constants::icase};
}  // namespace

Metric::Names scan_rrd(const std::filesystem::path &basedir,
                       const std::string &desc, Logger *logger) {
    Informational(logger) << "scanning for metrics of " << desc << " in "
                          << basedir;
    Metric::Names names;
    std::string line;
    auto path = basedir / pnp_cleanup(desc + ".xml");
    auto infile = std::ifstream{path};
    if (!infile.is_open()) {
        const auto ge = generic_error{"cannot open " + path.string()};
        Debug(logger) << ge;
        return {};
    }
    while (std::getline(infile, line)) {
        std::smatch label;
        std::regex_search(line, label, label_regex);
        if (!label.empty()) {
            names.emplace_back(label[1]);
        }
    }
    if (infile.bad()) {
        const auto ge = generic_error{"cannot read " + path.string()};
        Warning(logger) << ge;
    }
    return names;
}
