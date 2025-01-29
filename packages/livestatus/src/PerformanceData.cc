// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/PerformanceData.h"

#include <cctype>
#include <cstddef>
#include <cstdint>
#include <string_view>

using namespace std::string_view_literals;

// The states of our tiny finite state machine to parse the performance data.
enum class state : std::uint8_t {
    start,
    single_quoted,
    quote_within_quote,
    label,
    value,
    uom,
    warn,
    crit,
    min,
    max,
    error
};

// NOLINTNEXTLINE(readability-function-cognitive-complexity)
PerformanceData::PerformanceData(
    const std::string &perf_data,
    const std::string &default_check_command_name) {
    // Perfdata could contain a hint to the command name, like in
    // time=0.073836s;;;0.000000; size=557B;;;0; [check_http]. This is e.g.
    // being used by MRPE. There is an additional complication that some
    // brain-dead perf-data variable names contain brackets like in
    // [abcd.abc:service#ABCMetrics,JobsCount]=0;15000;15000.
    auto size = perf_data.size();
    while (size > 0 && isspace(perf_data[size - 1]) != 0) {
        size--;
    }
    if (size >= 2 && perf_data[size - 1] == ']') {
        const size_t pos = perf_data.rfind('[', size - 2);
        if (pos != std::string::npos) {
            _check_command_name = perf_data.substr(pos + 1, size - pos - 2);
            size = pos;
        }
    }
    if (_check_command_name.empty()) {
        _check_command_name = default_check_command_name;
    }

    size_t pos = 0;
    state s = state::start;
    std::string label;
    std::string value;
    std::string uom;
    std::string warn;
    std::string crit;
    std::string min;
    std::string max;
    while (pos <= size) {
        const char ch = pos == size ? ' ' : perf_data[pos];  // add sentinel
        pos++;
        switch (s) {
            case state::start:
                if (ch == '\'') {
                    label = "";
                    s = state::single_quoted;
                } else if (ch == '=') {
                    s = state::error;  // empty unquoted label
                } else if (isspace(ch) != 0) {
                    // skip initial space
                } else {
                    label = ch;
                    s = state::label;
                }
                break;
            case state::single_quoted:
                if (ch == '\'') {
                    s = state::quote_within_quote;
                } else {
                    label += ch;
                }
                break;
            case state::quote_within_quote:
                if (ch == '\'') {
                    label += ch;
                    s = state::single_quoted;
                } else if (ch == '=') {
                    value = "";
                    s = label.empty() ? state::error  // empty quoted label
                                      : state::value;
                } else {
                    s = state::error;  // funny char after quote
                }
                break;
            case state::label:
                if (ch == '\'' || isspace(ch) != 0) {
                    s = state::error;  // quote or space in label
                } else if (ch == '=') {
                    value = "";
                    s = state::value;
                } else {
                    label += ch;
                }
                break;
            case state::value:
                if ("0123456789+-,."sv.find_first_of(ch) !=
                    std::string_view::npos) {
                    value += ch;
                } else if (value.empty()) {
                    s = state::error;  // empty value
                } else if (ch == ';') {
                    warn = "";
                    s = state::warn;
                } else if (isspace(ch) != 0) {
                    addMetric(label, value, "", "", "", "", "");
                    s = state::start;
                } else {
                    uom = ch;
                    s = state::uom;
                }
                break;
            case state::uom:
                if (ch == ';') {
                    warn = "";
                    s = state::warn;
                } else if (isspace(ch) != 0) {
                    addMetric(label, value, uom, "", "", "", "");
                    s = state::start;
                } else {
                    uom += ch;
                }
                break;
            case state::warn:
                if (ch == ';') {
                    crit = "";
                    s = state::crit;
                } else if (isspace(ch) != 0) {
                    addMetric(label, value, uom, warn, "", "", "");
                    s = state::start;
                } else {
                    warn += ch;
                }
                break;
            case state::crit:
                if (ch == ';') {
                    min = "";
                    s = state::min;
                } else if (isspace(ch) != 0) {
                    addMetric(label, value, uom, warn, crit, "", "");
                    s = state::start;
                } else {
                    crit += ch;
                }
                break;
            case state::min:
                if (ch == ';') {
                    max = "";
                    s = state::max;
                } else if (isspace(ch) != 0) {
                    addMetric(label, value, uom, warn, crit, min, "");
                    s = state::start;
                } else {
                    min += ch;
                }
                break;
            case state::max:
                if (ch == ';') {
                    s = state::error;  // semicolon after max
                } else if (isspace(ch) != 0) {
                    addMetric(label, value, uom, warn, crit, min, max);
                    s = state::start;
                } else {
                    max += ch;
                }
                break;
            case state::error:
                if (isspace(ch) != 0) {  // re-sync until next metric
                    s = state::start;
                }
                break;
        }
    }
}

void PerformanceData::addMetric(const std::string &label,
                                const std::string &value,
                                const std::string &uom, const std::string &warn,
                                const std::string &crit, const std::string &min,
                                const std::string &max) {
    if (label.find('=') != std::string::npos) {
        // NOTE: The spec allows equal signs in labels, but our metrics system
        // is a bit fragile (read: buggy) regarding this, so we silently skip
        // such metrics.
        return;
    }
    _metrics.emplace_back(label, value, uom, warn, crit, min, max);
}
