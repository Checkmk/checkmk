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

#include "RRDColumn.h"
#include <rrd.h>
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iterator>
#include <ostream>
#include <set>
#include <tuple>
#include <type_traits>
#include <utility>
#include <vector>
#include "Logger.h"
#include "Metric.h"
#include "MonitoringCore.h"
#include "Renderer.h"
#include "Row.h"
#if defined(CMC)
#include "cmc.h"
#else
#include "nagios.h"
#endif
#include "strutil.h"

RRDColumn::RRDColumn(const std::string &name, const std::string &description,
                     const Column::Offsets &offsets, MonitoringCore *mc,
                     std::string rpn, time_t start_time, time_t end_time,
                     int resolution, int max_entries)
    : ListColumn(name, description, offsets)
    , _mc(mc)
    , _rpn(std::move(rpn))
    , _start_time(start_time)
    , _end_time(end_time)
    , _resolution(resolution)
    , _max_entries(max_entries) {}

void RRDColumn::output(Row row, RowRenderer &r, const contact * /* auth_user */,
                       std::chrono::seconds /*timezone_offset*/) const {
    // We output meta data as first elements in the list. Note: In Python or
    // JSON we could output nested lists. In CSV mode this is not possible and
    // we rather stay compatible with CSV mode.
    ListRenderer l(r);
    auto data = getData(row);
    l.output(data.start);
    l.output(data.end);
    l.output(data.step);
    for (const auto &value : data.values) {
        l.output(value);
    }
}

std::vector<std::string> RRDColumn::getValue(
    Row row, const contact * /*auth_user*/,
    std::chrono::seconds timezone_offset) const {
    auto data = getData(row);
    std::vector<std::string> strings;
    strings.push_back(std::to_string(
        std::chrono::system_clock::to_time_t(data.start + timezone_offset)));
    strings.push_back(std::to_string(
        std::chrono::system_clock::to_time_t(data.end + timezone_offset)));
    strings.push_back(std::to_string(data.step));
    std::transform(data.values.begin(), data.values.end(),
                   std::back_inserter(strings),
                   [](const auto &value) { return std::to_string(value); });
    return strings;
}

namespace {
bool isVariableName(const std::string &token) {
    auto is_operator = [](char c) { return strchr("+-/*", c) != nullptr; };
    auto is_number_part = [](char c) {
        return strchr("0123456789.", c) != nullptr;
    };

    return !(is_operator(token[0]) ||
             std::all_of(token.begin(), token.end(), is_number_part));
}

// TODO(sp): copy-n-paste from pnp4nagios.cc
std::string replace_all(const std::string &str, const std::string &chars,
                        char replacement) {
    std::string result(str);
    size_t i = 0;
    while ((i = result.find_first_of(chars, i)) != std::string::npos) {
        result[i++] = replacement;
    }
    return result;
}

std::pair<Metric::Name, std::string> getVarAndCF(const std::string &str) {
    size_t dot_pos = str.find_last_of('.');
    if (dot_pos != std::string::npos) {
        Metric::Name head{str.substr(0, dot_pos)};
        std::string tail = str.substr(dot_pos);
        if (tail == ".max") {
            return std::make_pair(head, "MAX");
        }
        if (tail == ".min") {
            return std::make_pair(head, "MIN");
        }
        if (tail == ".average") {
            return std::make_pair(head, "AVERAGE");
        }
    }
    return std::make_pair(Metric::Name{str}, "MAX");
}
};  // namespace

// TODO(mk): Convert all of the RPN expressions that are available in RRDTool
// and that have a different syntax then we have in our metrics system.
// >= --> GE. Or should we also go with GE instead of >=?
// Look at http://oss.oetiker.ch/rrdtool/doc/rrdgraph_rpn.en.html for details!
RRDColumn::Data RRDColumn::getData(Row row) const {
    Logger *logger = _mc->loggerRRD();

    // Get the host/service that all is about
    const auto *object = getObject(row);
    if (object == nullptr) {
        Warning(logger) << "Missing object pointer for RRDColumn";
        return {};
    }

    // Prepare the arguments for rrdtool xport in a dynamic array of strings.
    // Note: The actual step might be different!
    std::vector<std::string> argv_s{
        "rrdtool xport",  // name of program (ignored)
        "-s",
        std::to_string(_start_time),
        "-e",
        std::to_string(_end_time),
        "--step",
        std::to_string(_resolution)};

    if (_max_entries > 0) {
        argv_s.emplace_back("-m");
        argv_s.emplace_back(std::to_string(_max_entries));
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
    std::vector<char> rpn_copy(_rpn.begin(), _rpn.end());
    rpn_copy.push_back('\0');
    char *scan = &rpn_copy[0];

    // map from RRD variable names to perf variable names. The latter ones
    // can contain several special characters (like @ and -) which the RRD
    // variables cannot. The variable names are constructed with "var_%u"
    unsigned next_variable_number = 0;
    std::set<std::string> touched_rrds;

    while (const char *tok = next_token(&scan, ',')) {
        std::string token = tok;
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
        Metric::Name var{""};
        std::string cf;
        tie(var, cf) = getVarAndCF(token);

        auto location =
            _mc->metricLocation(object, Metric::MangledName(var), table());
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

    // Make RRDTool flush the rrdcached if neccessary

    // The cache deamon experiences long delays when queries extend over a
    // large time range and the underlying RRA are in high resolution.

    // For performance reasons the xport tool will not connect to the daemon
    // client to flush the data but will be done in 2 separate steps. First data
    // will be flush only. Then the xport tool will directly read the RRD file.

    // The performance issues with the cache daemon have been reported to
    // RRDTool on the issue
    // https://github.com/oetiker/rrdtool-1.x/issues/1062

    auto rrdcached_socket_path = _mc->rrdcachedSocketPath();
    if (!rrdcached_socket_path.empty()) {
        std::vector<std::string> daemon_argv_s{
            "rrdtool flushcached",  // name of program (ignored)
            "--daemon", rrdcached_socket_path};

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

        if (rrd_flushcached(static_cast<int>(daemon_argv_s.size()),
                            const_cast<char **>(&daemon_argv[0])) != 0) {
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

    // Now do the actual export. The library function rrd_xport mimicks the
    // command line API of rrd xport, but - fortunately - we get direct access
    // to a binary buffer with doubles. No parsing is required.
    int xxsize;
    time_t start;
    time_t end;
    unsigned long step;
    unsigned long col_cnt;
    char **legend_v;
    rrd_value_t *rrd_data;

    // Clear the RRD error float. RRDTool will not do this and immediately fail
    // if an error already occurred.
    rrd_clear_error();

    if (rrd_xport(static_cast<int>(argv_s.size()),
                  const_cast<char **>(&argv[0]), &xxsize, &start, &end, &step,
                  &col_cnt, &legend_v, &rrd_data) != 0) {
        Warning(logger) << "Error accessing RRD: " << rrd_get_error();
        return {};
    }

    // Since we have exactly one XPORT command, we expect exactly one column
    Data data;
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
        for (time_t ti = start + step; ti <= end; ti += step) {
            data.values.push_back(*ptr++);
        }
    }

    // rrd_xport uses malloc, so we *have* to use free.
    for (unsigned long j = 0; j < col_cnt; j++) {
        free(legend_v[j]);  // NOLINT
    }
    free(legend_v);  // NOLINT
    free(rrd_data);  // NOLINT
    return data;
}
