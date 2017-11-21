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

#include "PerfdataAggregator.h"
#include <cmath>
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
                consumeVariable(it->substr(0, pos),
                                std::stod(it->substr(pos + 1)));
            } catch (const std::logic_error &e) {
            }
        }
    }
}

void PerfdataAggregator::consumeVariable(const std::string &varname,
                                         double value) {
    auto it = _aggr.find(varname);
    if (it == _aggr.end()) {  // first entry
        perf_aggr new_entry;
        new_entry._count = 1;
        new_entry._aggr = value;
        new_entry._sumq = value * value;
        _aggr.emplace(varname, new_entry);
    } else {
        it->second._count++;
        switch (_operation) {
            case StatsOperation::sum:
                it->second._aggr += value;
                break;

            case StatsOperation::min:
                if (value < it->second._aggr) {
                    it->second._aggr = value;
                }
                break;

            case StatsOperation::max:
                if (value > it->second._aggr) {
                    it->second._aggr = value;
                }
                break;

            case StatsOperation::avg:
                it->second._aggr += value;
                break;

            case StatsOperation::std:
                it->second._aggr += value;
                it->second._sumq += value * value;
                break;

            case StatsOperation::suminv:
                it->second._aggr += 1.0 / value;
                break;

            case StatsOperation::avginv:
                it->second._aggr += 1.0 / value;
                break;
        }
    }
}

void PerfdataAggregator::output(RowRenderer &r) const {
    std::string perf_data;
    bool first = true;
    for (const auto &entry : _aggr) {
        double value;
        switch (_operation) {
            case StatsOperation::sum:
                value = entry.second._aggr;
                break;

            case StatsOperation::min:
                value = entry.second._aggr;
                break;

            case StatsOperation::max:
                value = entry.second._aggr;
                break;

            case StatsOperation::avg:
                value = entry.second._count == 0
                            ? 0.0
                            : (entry.second._aggr / entry.second._count);
                break;

            case StatsOperation::std:
                value = entry.second._count <= 1
                            ? 0.0
                            : sqrt((entry.second._sumq -
                                    (entry.second._aggr * entry.second._aggr) /
                                        entry.second._count) /
                                   (entry.second._count - 1));
                break;

            case StatsOperation::suminv:
                value = entry.second._aggr;
                break;

            case StatsOperation::avginv:
                value = entry.second._count == 0
                            ? 0.00
                            : (entry.second._aggr / entry.second._count);
                break;
        }
        if (first) {
            first = false;
        } else {
            perf_data += " ";
        }
        perf_data += entry.first + "=" + std::to_string(value);
    }
    r.output(perf_data);
}
