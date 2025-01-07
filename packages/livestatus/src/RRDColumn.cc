// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RRDColumn.h"

#include <rrd.h>

#include <algorithm>
#include <charconv>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <memory>
#include <set>
#include <stdexcept>
#include <string_view>
#include <system_error>

#include "livestatus/ICore.h"
#include "livestatus/Interface.h"
#include "livestatus/Logger.h"
#include "livestatus/Metric.h"
#include "livestatus/PnpUtils.h"
#include "livestatus/RRDFetch.h"

using namespace std::string_view_literals;

RRDColumnArgs::RRDColumnArgs(const std::string &arguments,
                             const std::string &column_name) {
    // We expect the following arguments: RPN:START_TIME:END_TIME:RESOLUTION
    // Example: fs_used,1024,/:1426411073:1426416473:5
    std::string_view args{arguments};
    auto invalid = [&column_name](const std::string &message) {
        throw std::runtime_error("invalid arguments for column '" +
                                 column_name + ": " + message);
    };
    auto next = [&args]() {
        auto field = args.substr(0, args.find(':'));
        args.remove_prefix(std::min(args.size(), field.size() + 1));
        return field;
    };
    auto next_non_empty = [&next, &invalid](const std::string &what) {
        auto field = next();
        if (field.empty()) {
            invalid("missing " + what);
        }
        return field;
    };
    auto parse_number = [&invalid](std::string_view str,
                                   const std::string &what) {
        auto value = 0;
        auto [ptr, ec] = std::from_chars(str.begin(), str.end(), value);
        // TODO(sp) Error handling
        if (ec != std::errc{} || ptr != str.end()) {
            invalid("invalid number for " + what);
        }
        return value;
    };
    auto next_number = [&next_non_empty,
                        &parse_number](const std::string &what) {
        return parse_number(next_non_empty(what), what);
    };

    this->rpn = next_non_empty("RPN expression");
    this->start_time = next_number("start time");
    this->end_time = next_number("end time");
    this->resolution = next_number("resolution");
    auto max_entries = next();
    this->max_entries = max_entries.empty()
                            ? 400
                            : parse_number(max_entries, "maximum entries");
    if (!args.empty()) {
        invalid("too many arguments");
    }
}

std::vector<RRDDataMaker::value_type> RRDDataMaker::operator()(
    const IHost &hst, std::chrono::seconds timezone_offset) const {
    return make(hst.name(), dummy_service_description(), timezone_offset);
}

std::vector<RRDDataMaker::value_type> RRDDataMaker::operator()(
    const IService &svc, std::chrono::seconds timezone_offset) const {
    return make(svc.host().name(), svc.description(), timezone_offset);
}

namespace {
bool isVariableName(std::string_view token) {
    auto is_operator = [](char c) {
        return "+-/*"sv.find_first_of(c) != std::string_view::npos;
    };
    auto is_number_part = [](char c) {
        return "0123456789."sv.find_first_of(c) != std::string_view::npos;
    };

    return !(is_operator(token[0]) ||
             std::ranges::all_of(token, is_number_part));
}

std::string replace_all(const std::string &str, const std::string &chars,
                        char replacement) {
    std::string result(str);
    size_t i = 0;
    while ((i = result.find_first_of(chars, i)) != std::string::npos) {
        result[i++] = replacement;
    }
    return result;
}

std::pair<Metric::Name, std::string> getVarAndCF(std::string_view str) {
    const size_t dot_pos = str.find_last_of('.');
    if (dot_pos != std::string::npos) {
        const Metric::Name head{std::string{str.substr(0, dot_pos)}};
        auto tail = str.substr(dot_pos);
        if (tail == ".max"sv) {
            return std::make_pair(head, "MAX");
        }
        if (tail == ".min"sv) {
            return std::make_pair(head, "MIN");
        }
        if (tail == ".average"sv) {
            return std::make_pair(head, "AVERAGE");
        }
    }
    return std::make_pair(Metric::Name{std::string{str}}, "MAX");
}

struct Data {
    RRDFetchHeader::time_point start;
    RRDFetchHeader::time_point end;
    unsigned long step{0};
    std::vector<double> values;

    [[nodiscard]] std::vector<RRDDataMaker::value_type> as_vector(
        std::chrono::seconds timezone_offset) const {
        // We output meta data as first elements in the list. Note: In Python or
        // JSON we could output nested lists. In CSV mode this is not possible
        // and we rather stay compatible with CSV mode.
        std::vector<RRDDataMaker::value_type> result;
        result.reserve(values.size() + 3);
        result.emplace_back(start + timezone_offset);
        result.emplace_back(end + timezone_offset);
        result.emplace_back(step);
        result.insert(result.end(), values.cbegin(), values.cend());
        return result;
    }
};
};  // namespace

// TODO(mk): Convert all of the RPN expressions that are available in RRDTool
// and that have a different syntax then we have in our metrics system.
// >= --> GE. Or should we also go with GE instead of >=?
// Look at http://oss.oetiker.ch/rrdtool/doc/rrdgraph_rpn.en.html for details!
// NOLINTNEXTLINE(readability-function-cognitive-complexity)
std::vector<RRDDataMaker::value_type> RRDDataMaker::make(
    const std::string &host_name, const std::string &service_description,
    std::chrono::seconds timezone_offset) const {
    // Prepare the arguments for rrdtool xport in a dynamic array of strings.
    // Note: The actual step might be different!
    std::vector<std::string> argv_s{
        "rrdtool xport",  // name of program (ignored)
        "-s",
        std::to_string(args_.start_time),
        "-e",
        std::to_string(args_.end_time),
        "--step",
        std::to_string(args_.resolution)};

    if (args_.max_entries > 0) {
        argv_s.emplace_back("-m");
        argv_s.emplace_back(std::to_string(args_.max_entries));
    }

    // We have an RPN like fs_used,1024,*. In order for that to work, we need to
    // create DEFs for all RRDs of the service first. The we create a CDEF with
    // our RPN and finally do the export. One difficulty here: we do not know
    // the exact variable names. The filenames of the RRDs have several
    // characters replaced with "_". This is a one-way escaping where we cannot
    // get back the original variable values. So the cleaner (an probably
    // faster) way is to look for the names of variables within our RPN
    // expressions and create DEFs just for them - if the according RRD exists.
    std::string converted_rpn;  // convert foo.max -> foo-max
    std::string_view rpn{args_.rpn};
    auto next = [&rpn]() {
        auto token = rpn.substr(0, rpn.find(','));
        rpn.remove_prefix(std::min(rpn.size(), token.size() + 1));
        return token;
    };

    // map from RRD variable names to perf variable names. The latter ones
    // can contain several special characters (like @ and -) which the RRD
    // variables cannot. The variable names are constructed with "var_%u"
    unsigned next_variable_number = 0;
    std::set<std::string> touched_rrds;

    while (!rpn.empty()) {
        auto token = next();
        if (!converted_rpn.empty()) {
            converted_rpn += ",";
        }
        if (!isVariableName(token)) {
            converted_rpn += token;
            continue;
        }

        // If the token looks like a variable name, then check if there is a
        // matching RRD and create a matching DEF: command if that is the
        // case. The token (assumed to be a metrics variable name) can contain a
        // '.' like e.g. in 'user.max', which select the consolidation function
        // MAX. RRDTool does not allow a variable name to contain a '.', but
        // strangely enough, it allows an underscore. Therefore, we replace '.'
        // by '_' here.
        auto [var, cf] = getVarAndCF(token);
        auto location =
            core_->metricLocation(host_name, service_description, var);
        std::string rrd_varname;
        if (location.path_.empty() || location.data_source_name_.empty()) {
            rrd_varname = replace_all(var.string(), ".", '_');
        } else {
            rrd_varname = "var_" + std::to_string(++next_variable_number);
            argv_s.push_back(std::string("DEF:")
                                 .append(rrd_varname)
                                 .append("=")
                                 .append(location.path_.string())
                                 .append(":")
                                 .append(location.data_source_name_)
                                 .append(":")
                                 .append(cf));
            touched_rrds.insert(location.path_.string());
        }
        converted_rpn += rrd_varname;
    }

    // Add the two commands for the actual export.
    argv_s.push_back("CDEF:xxx=" + converted_rpn);
    argv_s.emplace_back("XPORT:xxx:");

    // Make RRDTool flush the rrdcached if necessary

    // The cache daemon experiences long delays when queries extend over a
    // large time range and the underlying RRA are in high resolution.

    // For performance reasons the xport tool will not connect to the daemon
    // client to flush the data but will be done in 2 separate steps. First data
    // will be flush only. Then the xport tool will directly read the RRD file.

    // The performance issues with the cache daemon have been reported to
    // RRDTool on the issue
    // https://github.com/oetiker/rrdtool-1.x/issues/1062

    auto *logger = core_->loggerRRD();
    const auto rrdcached_socket = core_->paths()->rrdcached_socket();
    if (core_->pnp4nagiosEnabled() && !rrdcached_socket.empty() &&
        !touched_rrds.empty()) {
        std::vector<std::string> daemon_argv_s{
            "rrdtool flushcached",  // name of program (ignored)
            "--daemon", rrdcached_socket};

        for (const auto &rrdfile : touched_rrds) {
            daemon_argv_s.push_back(rrdfile);
        }

        // Convert our dynamic C++ string array to a C-style argv array
        std::vector<const char *> daemon_argv;
        daemon_argv.reserve(daemon_argv_s.size());
        for (const auto &arg : daemon_argv_s) {
            daemon_argv.push_back(arg.c_str());
        }
        daemon_argv.push_back(nullptr);

        if (logger->isLoggable(LogLevel::debug)) {
            Debug debug(logger);
            debug << "flush RRD data:";
            for (const auto &arg : daemon_argv_s) {
                debug << " " << arg;
            }
        }

        if (rrd_flushcached(
                static_cast<int>(daemon_argv_s.size()),
                // The RRD library is not const-correct.
                // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
                const_cast<char **>(daemon_argv.data())) != 0) {
            Warning(logger) << "Error flushing RRD: " << rrd_get_error();
        }
    }

    // Convert our dynamic C++ string array to a C-style argv array
    std::vector<const char *> argv;
    argv.reserve(argv_s.size());
    for (const auto &arg : argv_s) {
        argv.push_back(arg.c_str());
    }
    argv.push_back(nullptr);

    if (logger->isLoggable(LogLevel::debug)) {
        Debug debug(logger);
        debug << "retrieving RRD data:";
        for (const auto &arg : argv_s) {
            debug << " " << arg;
        }
    }

    // Now do the actual export. The library function rrd_xport mimics the
    // command line API of rrd xport, but - fortunately - we get direct access
    // to a binary buffer with doubles. No parsing is required.
    int xxsize = 0;
    time_t start = 0;
    time_t end = 0;
    unsigned long step = 0;
    unsigned long col_cnt = 0;
    char **legend_v = nullptr;
    rrd_value_t *rrd_data = nullptr;

    // Clear the RRD error float. RRDTool will not do this and immediately fail
    // if an error already occurred.
    rrd_clear_error();

    Data data;
    if (rrd_xport(static_cast<int>(argv_s.size()),
                  // The RRD library is not const-correct.
                  // NOLINTNEXTLINE(cppcoreguidelines-pro-type-const-cast)
                  const_cast<char **>(argv.data()), &xxsize, &start, &end,
                  &step, &col_cnt, &legend_v, &rrd_data) != 0) {
        const std::string rrd_error{rrd_get_error()};
        if (rrd_error.starts_with("don't understand ")) {
            // The error msg "don't understand '<metric_name>'" is logged on
            // info lvl only as preventing such queries for non-given metrics is
            // not feasible atm
            Informational(logger)
                << "Error parsing RPN expression: " << rrd_error;
        } else {
            Warning(logger) << "Error accessing RRD: " << rrd_error;
        }
        return data.as_vector(timezone_offset);
    }

    // Since we have exactly one XPORT command, we expect exactly one column
    if (col_cnt != 1) {
        Error(logger) << "rrd_xport returned " << col_cnt
                      << " columns, but exactly one was expected.";
    } else {
        // XPORT takes a closed timewindow in its query and returns the
        // timestamped values that represent an intersection with the query
        // window. The returned interval description is right closed.

        // The timestamps associated with a value in RRDtool ALWAYS
        // represent the time the sample was taken. Since any value you
        // sample will represent some sort of past state your sampling
        // apparatus has gathered, the timestamp will always be at the end
        // of the sampling period

        // LEGEND
        // O timestamps of measurements
        // | query values, _start_time and _end_time
        // x returned start, no data contained
        // v returned data rows, includes end y

        // --O---O---O---O---O---O---O---O
        //         |---------------|
        //       x---v---v---v---v---y

        // Exact start time of the represented interval(x). This is <= our
        // _start_time(|), but no value is associated to this time.
        data.start = std::chrono::system_clock::from_time_t(start);
        // Time closing time of the interval(y). This is >= our _end_time, and
        // holds the last data value.
        data.end = std::chrono::system_clock::from_time_t(end);
        // Actual resolution in seconds. This is >= our _resolution
        data.step = step;
        // Now the actual data - double for double
        // Data rows represent past values, thus loop starts with step shift.
        // Interval is right closed, thus iterate until end inclusive.
        rrd_value_t *ptr = rrd_data;
        // NOLINTNEXTLINE(bugprone-narrowing-conversions,cppcoreguidelines-narrowing-conversions)
        for (time_t ti = start + step; ti <= end; ti += step) {
            // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
            data.values.push_back(*ptr++);
        }
    }

    // rrd_xport uses malloc, so we *have* to use free.
    // NOLINTBEGIN(cppcoreguidelines-no-malloc,cppcoreguidelines-owning-memory)
    for (unsigned long j = 0; j < col_cnt; j++) {
        // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic)
        ::free(legend_v[j]);
    }
    // NOLINTNEXTLINE(bugprone-multi-level-implicit-pointer-conversion)
    ::free(legend_v);
    ::free(rrd_data);
    // NOLINTEND(cppcoreguidelines-no-malloc,cppcoreguidelines-owning-memory)
    return data.as_vector(timezone_offset);
}
