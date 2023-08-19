// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/PerfdataAggregator.h"

#include <cmath>
#include <iterator>
#include <sstream>
#include <stdexcept>

#include "livestatus/Renderer.h"
#include "livestatus/Row.h"

void PerfdataAggregator::consume(Row row, const User & /*user*/,
                                 std::chrono::seconds /*timezone_offset*/) {
    std::istringstream iss(_getValue(row));
    const std::istream_iterator<std::string> end;
    for (auto it = std::istream_iterator<std::string>(iss); it != end; ++it) {
        auto pos = it->find('=');
        if (pos != std::string::npos) {
            try {
                auto varname = it->substr(0, pos);
                auto value = std::stod(it->substr(pos + 1));
                _aggregations.insert(std::make_pair(varname, _factory()))
                    .first->second->update(value);
            } catch (const std::logic_error &e) {
                // A no-op just to make clang-tidy happy: std::stod() failed and
                // skipping the var/value pair is really what we want to do.
                continue;
            }
        }
    }
}

void PerfdataAggregator::output(RowRenderer &r) const {
    std::string perf_data;
    bool first = true;
    for (const auto &entry : _aggregations) {
        const double value = entry.second->value();
        if (std::isfinite(value)) {
            if (first) {
                first = false;
            } else {
                perf_data += " ";
            }
            perf_data += entry.first + "=" + std::to_string(value);
        }
    }
    r.output(perf_data);
}
