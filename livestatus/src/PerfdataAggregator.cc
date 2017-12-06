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

// IWYU pragma: no_include <type_traits>
#include "PerfdataAggregator.h"
#include <cmath>
#include <functional>
#include <iterator>
#include <sstream>
#include <stdexcept>
#include <utility>
#include "Renderer.h"
#include "Row.h"
#include "StringColumn.h"
#include "contact_fwd.h"

void PerfdataAggregator::consume(Row row, const contact * /* auth_user */,
                                 std::chrono::seconds /* timezone_offset */) {
    std::istringstream iss(_column->getValue(row));
    std::istream_iterator<std::string> end;
    for (auto it = std::istream_iterator<std::string>(iss); it != end; ++it) {
        auto pos = it->find('=');
        if (pos != std::string::npos) {
            try {
                auto varname = it->substr(0, pos);
                auto value = std::stod(it->substr(pos + 1));
                _aggregations.insert(std::make_pair(varname, _factory()))
                    .first->second->update(value);
            } catch (const std::logic_error &e) {
            }
        }
    }
}

void PerfdataAggregator::output(RowRenderer &r) const {
    std::string perf_data;
    bool first = true;
    for (const auto &entry : _aggregations) {
        double value = entry.second->value();
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
